from datetime import datetime

from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class Component(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(index=True)
    subcategory: Mapped[str | None] = mapped_column()
    value: Mapped[str] = mapped_column(index=True)
    value_numeric: Mapped[float | None] = mapped_column()
    value_unit: Mapped[str | None] = mapped_column()
    package: Mapped[str | None] = mapped_column()
    description: Mapped[str | None] = mapped_column()
    manufacturer: Mapped[str | None] = mapped_column()
    mpn: Mapped[str | None] = mapped_column()
    quantity: Mapped[int] = mapped_column(default=0)
    min_quantity: Mapped[int] = mapped_column(default=0)
    location: Mapped[str | None] = mapped_column(index=True)
    notes: Mapped[str | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    transactions: Mapped[list["InventoryTransaction"]] = relationship(back_populates="component")
    supplier_listings: Mapped[list["SupplierListing"]] = relationship(back_populates="component")
    bom_items: Mapped[list["BOMItem"]] = relationship(back_populates="component")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        Index("idx_inv_tx_component", "component_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"))
    delta: Mapped[int] = mapped_column()
    reason: Mapped[str] = mapped_column()
    build_id: Mapped[int | None] = mapped_column(ForeignKey("builds.id"))
    note: Mapped[str | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    component: Mapped["Component"] = relationship(back_populates="transactions")
