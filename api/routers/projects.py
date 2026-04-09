from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.project import BOMItem, Project
from api.schemas.project import (
    BOMItemCreate,
    BOMItemRead,
    BOMItemUpdate,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(
    status: str | None = None,
    effect_type: str | None = None,
    q: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(Project)
    if status:
        stmt = stmt.where(Project.status == status)
    if effect_type:
        stmt = stmt.where(Project.effect_type == effect_type)
    if q:
        stmt = stmt.where(Project.name.ilike(f"%{q}%") | Project.description.ilike(f"%{q}%"))
    stmt = stmt.order_by(Project.updated_at.desc()).offset(offset).limit(limit)
    return db.scalars(stmt).all()


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(project, key, val)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    db.delete(project)
    db.commit()


# --- BOM Items ---

@router.get("/{project_id}/bom", response_model=list[BOMItemRead])
def list_bom_items(project_id: int, db: Session = Depends(get_db)):
    stmt = select(BOMItem).where(BOMItem.project_id == project_id).order_by(BOMItem.reference)
    return db.scalars(stmt).all()


@router.post("/{project_id}/bom", response_model=BOMItemRead, status_code=201)
def add_bom_item(project_id: int, data: BOMItemCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    item = BOMItem(project_id=project_id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{project_id}/bom/{item_id}", response_model=BOMItemRead)
def update_bom_item(project_id: int, item_id: int, data: BOMItemUpdate, db: Session = Depends(get_db)):
    item = db.get(BOMItem, item_id)
    if not item or item.project_id != project_id:
        raise HTTPException(404, "BOM item not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(item, key, val)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{project_id}/bom/{item_id}", status_code=204)
def delete_bom_item(project_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.get(BOMItem, item_id)
    if not item or item.project_id != project_id:
        raise HTTPException(404, "BOM item not found")
    db.delete(item)
    db.commit()


@router.post("/{project_id}/bom/import", response_model=list[BOMItemRead], status_code=201)
def import_bom(project_id: int, file: UploadFile, db: Session = Depends(get_db)):
    from api.services.bom_parser import parse_bom_file

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    content = file.file.read()
    items_data = parse_bom_file(content, file.filename or "bom.csv")
    items = []
    for item_data in items_data:
        item = BOMItem(project_id=project_id, **item_data)
        db.add(item)
        items.append(item)
    db.commit()
    for item in items:
        db.refresh(item)
    return items
