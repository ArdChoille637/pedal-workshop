from datetime import datetime

from sqlalchemy import Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base


class Schematic(Base):
    __tablename__ = "schematics"
    __table_args__ = (
        UniqueConstraint("category_folder", "file_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_folder: Mapped[str] = mapped_column(String(200), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(10))
    file_size: Mapped[int | None] = mapped_column(Integer)
    effect_type: Mapped[str | None] = mapped_column(String(50), index=True)
    tags: Mapped[str | None] = mapped_column(Text)  # JSON array
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    def __repr__(self) -> str:
        return f"<Schematic {self.file_name}>"
