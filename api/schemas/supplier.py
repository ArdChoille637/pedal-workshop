from datetime import datetime

from pydantic import BaseModel


class SupplierBase(BaseModel):
    name: str
    slug: str
    website: str | None = None
    api_type: str = "scrape"
    poll_enabled: int = 1
    poll_interval: int = 86400


class SupplierCreate(SupplierBase):
    pass


class SupplierRead(SupplierBase):
    id: int
    last_polled_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SupplierListingBase(BaseModel):
    component_id: int
    supplier_id: int
    sku: str
    url: str | None = None
    unit_price: float | None = None
    currency: str = "USD"
    price_break_json: str | None = None
    in_stock: int | None = None
    stock_quantity: int | None = None


class SupplierListingCreate(SupplierListingBase):
    pass


class SupplierListingRead(SupplierListingBase):
    id: int
    last_checked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PriceSnapshotRead(BaseModel):
    id: int
    supplier_listing_id: int
    unit_price: float
    in_stock: int | None
    stock_quantity: int | None
    recorded_at: datetime

    model_config = {"from_attributes": True}
