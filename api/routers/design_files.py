import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.models.design_file import DesignFile
from api.models.project import Project

router = APIRouter(prefix="/api/design-files", tags=["design-files"])

FILE_TYPE_MAP = {
    ".fcstd": "freecad",
    ".lpp": "librepcb",
    ".gbr": "gerber",
    ".drl": "drill",
    ".csv": "bom_export",
    ".pdf": "schematic_pdf",
    ".png": "photo",
    ".jpg": "photo",
    ".jpeg": "photo",
}


@router.post("/projects/{project_id}/upload", status_code=201)
def upload_design_file(
    project_id: int,
    file: UploadFile,
    version: str = "v1",
    description: str = "",
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    ext = Path(file.filename or "").suffix.lower()
    file_type = FILE_TYPE_MAP.get(ext, "other")

    rel_dir = Path(project.slug) / version
    abs_dir = Path(settings.design_files_dir) / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)

    file_path = abs_dir / (file.filename or "upload")
    content = file.file.read()
    file_path.write_bytes(content)

    design_file = DesignFile(
        project_id=project_id,
        file_type=file_type,
        file_name=file.filename or "upload",
        file_path=str(rel_dir / (file.filename or "upload")),
        version=version,
        description=description,
        file_size=len(content),
        mime_type=file.content_type,
    )
    db.add(design_file)
    db.commit()
    db.refresh(design_file)
    return design_file


@router.get("/projects/{project_id}", response_model=list)
def list_design_files(project_id: int, db: Session = Depends(get_db)):
    stmt = select(DesignFile).where(DesignFile.project_id == project_id).order_by(DesignFile.version, DesignFile.file_name)
    return db.scalars(stmt).all()


@router.get("/{file_id}/download")
def download_design_file(file_id: int, db: Session = Depends(get_db)):
    design_file = db.get(DesignFile, file_id)
    if not design_file:
        raise HTTPException(404, "Design file not found")

    abs_path = Path(settings.design_files_dir) / design_file.file_path
    if not abs_path.is_file():
        raise HTTPException(404, "File not found on disk")

    return FileResponse(abs_path, filename=design_file.file_name)


@router.delete("/{file_id}", status_code=204)
def delete_design_file(file_id: int, db: Session = Depends(get_db)):
    design_file = db.get(DesignFile, file_id)
    if not design_file:
        raise HTTPException(404, "Design file not found")

    abs_path = Path(settings.design_files_dir) / design_file.file_path
    if abs_path.is_file():
        abs_path.unlink()

    db.delete(design_file)
    db.commit()
