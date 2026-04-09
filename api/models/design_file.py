from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class DesignFile(Base):
    __tablename__ = "design_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    file_type: Mapped[str] = mapped_column()
    file_name: Mapped[str] = mapped_column()
    file_path: Mapped[str] = mapped_column()
    version: Mapped[str | None] = mapped_column()
    description: Mapped[str | None] = mapped_column()
    file_size: Mapped[int | None] = mapped_column()
    mime_type: Mapped[str | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    project: Mapped["Project"] = relationship(back_populates="design_files")
