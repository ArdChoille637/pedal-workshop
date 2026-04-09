from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str | None] = mapped_column()
    status: Mapped[str] = mapped_column(default="planned")
    quantity: Mapped[int] = mapped_column(default=1)
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    notes: Mapped[str | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="builds")
    status_log: Mapped[list["BuildStatusLog"]] = relationship(back_populates="build", cascade="all, delete-orphan")


class BuildStatusLog(Base):
    __tablename__ = "build_status_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    build_id: Mapped[int] = mapped_column(ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    old_status: Mapped[str | None] = mapped_column()
    new_status: Mapped[str] = mapped_column()
    note: Mapped[str | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    build: Mapped["Build"] = relationship(back_populates="status_log")
