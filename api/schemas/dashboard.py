from pydantic import BaseModel


class CheapestSource(BaseModel):
    supplier: str
    price: float | None
    in_stock: bool | None


class MissingPart(BaseModel):
    bom_item_id: int
    reference: str | None
    category: str
    value: str
    shortfall: int
    cheapest_source: CheapestSource | None = None


class ProjectBuildStatus(BaseModel):
    project_id: int
    project_name: str
    effect_type: str | None
    status: str
    bom_count: int
    missing_count: int
    missing_parts: list[MissingPart] = []
    estimated_cost: float | None = None


class DashboardResponse(BaseModel):
    ready: list[ProjectBuildStatus]
    arna_1_3: list[ProjectBuildStatus]
    arna_4_plus: list[ProjectBuildStatus]


class LowStockItem(BaseModel):
    component_id: int
    category: str
    value: str
    quantity: int
    min_quantity: int
    location: str | None


class DashboardSummary(BaseModel):
    total_components: int
    total_unique_parts: int
    total_projects: int
    active_builds: int
    low_stock_count: int
    ready_to_build: int
    arna_1_3: int
    arna_4_plus: int
