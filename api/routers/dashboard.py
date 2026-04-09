from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.build import Build
from api.models.component import Component
from api.models.project import Project
from api.schemas.dashboard import DashboardResponse, DashboardSummary, LowStockItem
from api.services.build_analyzer import analyze_build_tiers

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/build-tiers", response_model=DashboardResponse)
def get_build_tiers(db: Session = Depends(get_db)):
    return analyze_build_tiers(db)


@router.get("/low-stock", response_model=list[LowStockItem])
def get_low_stock(db: Session = Depends(get_db)):
    stmt = (
        select(Component)
        .where(Component.quantity <= Component.min_quantity, Component.min_quantity > 0)
        .order_by(Component.category, Component.value)
    )
    components = db.scalars(stmt).all()
    return [
        LowStockItem(
            component_id=c.id,
            category=c.category,
            value=c.value,
            quantity=c.quantity,
            min_quantity=c.min_quantity,
            location=c.location,
        )
        for c in components
    ]


@router.get("/summary", response_model=DashboardSummary)
def get_summary(db: Session = Depends(get_db)):
    total_qty = db.scalar(select(func.sum(Component.quantity))) or 0
    unique_parts = db.scalar(select(func.count(Component.id))) or 0
    total_projects = db.scalar(select(func.count(Project.id))) or 0
    active_builds = db.scalar(
        select(func.count(Build.id)).where(Build.status.in_(["planned", "pulling_parts", "in_progress", "testing"]))
    ) or 0
    low_stock = db.scalar(
        select(func.count(Component.id)).where(Component.quantity <= Component.min_quantity, Component.min_quantity > 0)
    ) or 0

    tiers = analyze_build_tiers(db)

    return DashboardSummary(
        total_components=total_qty,
        total_unique_parts=unique_parts,
        total_projects=total_projects,
        active_builds=active_builds,
        low_stock_count=low_stock,
        ready_to_build=len(tiers.ready),
        arna_1_3=len(tiers.arna_1_3),
        arna_4_plus=len(tiers.arna_4_plus),
    )
