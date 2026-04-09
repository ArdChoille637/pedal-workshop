from datetime import datetime

from pydantic import BaseModel


class ComponentBase(BaseModel):
    category: str
    subcategory: str | None = None
    value: str
    value_numeric: float | None = None
    value_unit: str | None = None
    package: str | None = None
    description: str | None = None
    manufacturer: str | None = None
    mpn: str | None = None
    quantity: int = 0
    min_quantity: int = 0
    location: str | None = None
    notes: str | None = None


class ComponentCreate(ComponentBase):
    pass


class ComponentUpdate(BaseModel):
    category: str | None = None
    subcategory: str | None = None
    value: str | None = None
    value_numeric: float | None = None
    value_unit: str | None = None
    package: str | None = None
    description: str | None = None
    manufacturer: str | None = None
    mpn: str | None = None
    quantity: int | None = None
    min_quantity: int | None = None
    location: str | None = None
    notes: str | None = None


class ComponentRead(ComponentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuantityAdjust(BaseModel):
    delta: int
    reason: str = "adjustment"
    note: str | None = None


class InventoryTransactionRead(BaseModel):
    id: int
    component_id: int
    delta: int
    reason: str
    build_id: int | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
