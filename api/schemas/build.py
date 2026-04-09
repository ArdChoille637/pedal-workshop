from datetime import datetime

from pydantic import BaseModel


class BuildBase(BaseModel):
    project_id: int
    name: str | None = None
    quantity: int = 1
    notes: str | None = None


class BuildCreate(BuildBase):
    pass


class BuildRead(BuildBase):
    id: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BuildStatusUpdate(BaseModel):
    status: str
    note: str | None = None


class BuildStatusLogRead(BaseModel):
    id: int
    build_id: int
    old_status: str | None
    new_status: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
