from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    slug: Mapped[str] = mapped_column(unique=True)
    effect_type: Mapped[str | None] = mapped_column()
    status: Mapped[str] = mapped_column(default="design")
    description: Mapped[str | None] = mapped_column()
    notes: Mapped[str | None] = mapped_column()
    schematic_id: Mapped[int | None] = mapped_column(ForeignKey("schematics.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    bom_items: Mapped[list["BOMItem"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    builds: Mapped[list["Build"]] = relationship(back_populates="project")
    design_files: Mapped[list["DesignFile"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class BOMItem(Base):
    __tablename__ = "bom_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    component_id: Mapped[int | None] = mapped_column(ForeignKey("components.id", ondelete="SET NULL"), index=True)
    reference: Mapped[str | None] = mapped_column()
    category: Mapped[str] = mapped_column()
    value: Mapped[str] = mapped_column()
    quantity: Mapped[int] = mapped_column(default=1)
    notes: Mapped[str | None] = mapped_column()
    is_optional: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    project: Mapped["Project"] = relationship(back_populates="bom_items")
    component: Mapped["Component | None"] = relationship(back_populates="bom_items")
