from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.models.schematic import Schematic

router = APIRouter(prefix="/api/schematics", tags=["schematics"])


@router.get("")
def list_schematics(
    category: str | None = None,
    effect_type: str | None = None,
    q: str | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(Schematic)
    if category:
        stmt = stmt.where(Schematic.category_folder == category)
    if effect_type:
        stmt = stmt.where(Schematic.effect_type == effect_type)
    if q:
        stmt = stmt.where(
            Schematic.file_name.ilike(f"%{q}%") | Schematic.tags.ilike(f"%{q}%")
        )
    stmt = stmt.order_by(Schematic.category_folder, Schematic.file_name).offset(offset).limit(limit)
    return db.scalars(stmt).all()


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    stmt = select(Schematic.category_folder).distinct().order_by(Schematic.category_folder)
    return db.scalars(stmt).all()


@router.get("/{schematic_id}")
def get_schematic(schematic_id: int, db: Session = Depends(get_db)):
    schematic = db.get(Schematic, schematic_id)
    if not schematic:
        raise HTTPException(404, "Schematic not found")
    return schematic


@router.get("/{schematic_id}/file")
def serve_schematic_file(schematic_id: int, db: Session = Depends(get_db)):
    schematic = db.get(Schematic, schematic_id)
    if not schematic:
        raise HTTPException(404, "Schematic not found")

    file_path = Path(settings.schematics_root) / schematic.file_path
    resolved = file_path.resolve()

    # Prevent directory traversal
    schematics_root = Path(settings.schematics_root).resolve()
    if not str(resolved).startswith(str(schematics_root)):
        raise HTTPException(403, "Access denied")

    if not resolved.is_file():
        raise HTTPException(404, "File not found on disk")

    return FileResponse(resolved)
