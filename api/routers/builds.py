from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.build import Build, BuildStatusLog
from api.models.component import Component, InventoryTransaction
from api.models.project import BOMItem
from api.schemas.build import BuildCreate, BuildRead, BuildStatusLogRead, BuildStatusUpdate

router = APIRouter(prefix="/api/builds", tags=["builds"])

VALID_TRANSITIONS = {
    "planned": ["pulling_parts", "cancelled"],
    "pulling_parts": ["in_progress", "planned", "cancelled"],
    "in_progress": ["testing", "failed", "cancelled"],
    "testing": ["complete", "in_progress", "failed"],
    "failed": ["in_progress", "planned"],
    "complete": [],
    "cancelled": ["planned"],
}


@router.get("", response_model=list[BuildRead])
def list_builds(
    status: str | None = None,
    project_id: int | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(Build)
    if status:
        stmt = stmt.where(Build.status == status)
    if project_id:
        stmt = stmt.where(Build.project_id == project_id)
    stmt = stmt.order_by(Build.created_at.desc()).offset(offset).limit(limit)
    return db.scalars(stmt).all()


@router.post("", response_model=BuildRead, status_code=201)
def create_build(data: BuildCreate, db: Session = Depends(get_db)):
    build = Build(**data.model_dump())
    db.add(build)
    db.flush()
    log = BuildStatusLog(build_id=build.id, old_status=None, new_status="planned")
    db.add(log)
    db.commit()
    db.refresh(build)
    return build


@router.get("/{build_id}", response_model=BuildRead)
def get_build(build_id: int, db: Session = Depends(get_db)):
    build = db.get(Build, build_id)
    if not build:
        raise HTTPException(404, "Build not found")
    return build


@router.patch("/{build_id}/status", response_model=BuildRead)
def update_build_status(build_id: int, data: BuildStatusUpdate, db: Session = Depends(get_db)):
    build = db.get(Build, build_id)
    if not build:
        raise HTTPException(404, "Build not found")
    allowed = VALID_TRANSITIONS.get(build.status, [])
    if data.status not in allowed:
        raise HTTPException(400, f"Cannot transition from '{build.status}' to '{data.status}'. Allowed: {allowed}")
    old_status = build.status
    build.status = data.status
    now = datetime.now(timezone.utc)
    if data.status == "in_progress" and not build.started_at:
        build.started_at = now
    elif data.status == "complete":
        build.completed_at = now
    log = BuildStatusLog(build_id=build_id, old_status=old_status, new_status=data.status, note=data.note)
    db.add(log)
    db.commit()
    db.refresh(build)
    return build


@router.get("/{build_id}/log", response_model=list[BuildStatusLogRead])
def get_build_log(build_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(BuildStatusLog)
        .where(BuildStatusLog.build_id == build_id)
        .order_by(BuildStatusLog.created_at)
    )
    return db.scalars(stmt).all()


@router.post("/{build_id}/pull-parts", response_model=BuildRead)
def pull_parts(build_id: int, db: Session = Depends(get_db)):
    """Deduct BOM quantities from inventory for this build."""
    build = db.get(Build, build_id)
    if not build:
        raise HTTPException(404, "Build not found")
    if build.status not in ("planned", "pulling_parts"):
        raise HTTPException(400, "Can only pull parts for planned or pulling_parts builds")

    bom_items = db.scalars(
        select(BOMItem)
        .where(BOMItem.project_id == build.project_id, BOMItem.is_optional == 0)
    ).all()

    errors = []
    for item in bom_items:
        if not item.component_id:
            errors.append(f"{item.reference or item.value}: not linked to inventory")
            continue
        component = db.get(Component, item.component_id)
        if not component:
            errors.append(f"{item.reference or item.value}: component not found")
            continue
        needed = item.quantity * build.quantity
        if component.quantity < needed:
            errors.append(f"{item.reference or item.value}: need {needed}, have {component.quantity}")
            continue

    if errors:
        raise HTTPException(400, detail={"message": "Insufficient inventory", "errors": errors})

    for item in bom_items:
        if not item.component_id:
            continue
        component = db.get(Component, item.component_id)
        needed = item.quantity * build.quantity
        component.quantity -= needed
        tx = InventoryTransaction(
            component_id=item.component_id,
            delta=-needed,
            reason="build_consume",
            build_id=build.id,
            note=f"Pulled for build #{build.id} ({build.name})",
        )
        db.add(tx)

    if build.status == "planned":
        build.status = "pulling_parts"
        log = BuildStatusLog(build_id=build.id, old_status="planned", new_status="pulling_parts", note="Parts pulled from inventory")
        db.add(log)

    db.commit()
    db.refresh(build)
    return build
