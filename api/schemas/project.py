from datetime import datetime

from pydantic import BaseModel


class ProjectBase(BaseModel):
    name: str
    slug: str
    effect_type: str | None = None
    status: str = "design"
    description: str | None = None
    notes: str | None = None
    schematic_id: int | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    effect_type: str | None = None
    status: str | None = None
    description: str | None = None
    notes: str | None = None
    schematic_id: int | None = None


class ProjectRead(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BOMItemBase(BaseModel):
    component_id: int | None = None
    reference: str | None = None
    category: str
    value: str
    quantity: int = 1
    notes: str | None = None
    is_optional: int = 0


class BOMItemCreate(BOMItemBase):
    pass


class BOMItemUpdate(BaseModel):
    component_id: int | None = None
    reference: str | None = None
    category: str | None = None
    value: str | None = None
    quantity: int | None = None
    notes: str | None = None
    is_optional: int | None = None


class BOMItemRead(BOMItemBase):
    id: int
    project_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
