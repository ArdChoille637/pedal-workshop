from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    slug: Mapped[str] = mapped_column(unique=True)
    website: Mapped[str | None] = mapped_column()
    api_type: Mapped[str] = mapped_column()
    poll_enabled: Mapped[int] = mapped_column(default=1)
    poll_interval: Mapped[int] = mapped_column(default=86400)
    last_polled_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    listings: Mapped[list["SupplierListing"]] = relationship(back_populates="supplier")


class SupplierListing(Base):
    __tablename__ = "supplier_listings"
    __table_args__ = (
        UniqueConstraint("component_id", "supplier_id", "sku"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column()
    url: Mapped[str | None] = mapped_column()
    unit_price: Mapped[float | None] = mapped_column()
    currency: Mapped[str] = mapped_column(default="USD")
    price_break_json: Mapped[str | None] = mapped_column()
    in_stock: Mapped[int | None] = mapped_column()
    stock_quantity: Mapped[int | None] = mapped_column()
    last_checked_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    supplier: Mapped["Supplier"] = relationship(back_populates="listings")
    component: Mapped["Component"] = relationship(back_populates="supplier_listings")
    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="listing")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (
        Index("idx_price_snapshots_listing", "supplier_listing_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_listing_id: Mapped[int] = mapped_column(ForeignKey("supplier_listings.id", ondelete="CASCADE"), index=True)
    unit_price: Mapped[float] = mapped_column()
    in_stock: Mapped[int | None] = mapped_column()
    stock_quantity: Mapped[int | None] = mapped_column()
    recorded_at: Mapped[datetime] = mapped_column(default=func.now())

    listing: Mapped["SupplierListing"] = relationship(back_populates="price_snapshots")
