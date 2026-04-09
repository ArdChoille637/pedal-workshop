from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.component import Component, InventoryTransaction
from api.schemas.component import (
    ComponentCreate,
    ComponentRead,
    ComponentUpdate,
    InventoryTransactionRead,
    QuantityAdjust,
)

router = APIRouter(prefix="/api/components", tags=["components"])


@router.get("", response_model=list[ComponentRead])
def list_components(
    category: str | None = None,
    value: str | None = None,
    location: str | None = None,
    low_stock: bool = False,
    q: str | None = None,
    limit: int = Query(default=200, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(Component)
    if category:
        stmt = stmt.where(Component.category == category)
    if value:
        stmt = stmt.where(Component.value.ilike(f"%{value}%"))
    if location:
        stmt = stmt.where(Component.location.ilike(f"%{location}%"))
    if low_stock:
        stmt = stmt.where(Component.quantity <= Component.min_quantity)
    if q:
        stmt = stmt.where(
            Component.value.ilike(f"%{q}%")
            | Component.description.ilike(f"%{q}%")
            | Component.manufacturer.ilike(f"%{q}%")
            | Component.mpn.ilike(f"%{q}%")
        )
    stmt = stmt.order_by(Component.category, Component.value).offset(offset).limit(limit)
    return db.scalars(stmt).all()


@router.post("", response_model=ComponentRead, status_code=201)
def create_component(data: ComponentCreate, db: Session = Depends(get_db)):
    component = Component(**data.model_dump())
    db.add(component)
    if component.quantity > 0:
        tx = InventoryTransaction(
            component_id=0,  # placeholder, set after flush
            delta=component.quantity,
            reason="initial",
            note="Initial stock on creation",
        )
        db.add(tx)
        db.flush()
        tx.component_id = component.id
    db.commit()
    db.refresh(component)
    return component


@router.get("/{component_id}", response_model=ComponentRead)
def get_component(component_id: int, db: Session = Depends(get_db)):
    component = db.get(Component, component_id)
    if not component:
        raise HTTPException(404, "Component not found")
    return component


@router.put("/{component_id}", response_model=ComponentRead)
def update_component(component_id: int, data: ComponentUpdate, db: Session = Depends(get_db)):
    component = db.get(Component, component_id)
    if not component:
        raise HTTPException(404, "Component not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(component, key, val)
    db.commit()
    db.refresh(component)
    return component


@router.delete("/{component_id}", status_code=204)
def delete_component(component_id: int, db: Session = Depends(get_db)):
    component = db.get(Component, component_id)
    if not component:
        raise HTTPException(404, "Component not found")
    db.delete(component)
    db.commit()


@router.patch("/{component_id}/quantity", response_model=ComponentRead)
def adjust_quantity(component_id: int, adj: QuantityAdjust, db: Session = Depends(get_db)):
    component = db.get(Component, component_id)
    if not component:
        raise HTTPException(404, "Component not found")
    component.quantity += adj.delta
    if component.quantity < 0:
        raise HTTPException(400, "Quantity cannot go below zero")
    tx = InventoryTransaction(
        component_id=component_id,
        delta=adj.delta,
        reason=adj.reason,
        note=adj.note,
    )
    db.add(tx)
    db.commit()
    db.refresh(component)
    return component


@router.get("/{component_id}/transactions", response_model=list[InventoryTransactionRead])
def get_transactions(component_id: int, limit: int = 50, db: Session = Depends(get_db)):
    stmt = (
        select(InventoryTransaction)
        .where(InventoryTransaction.component_id == component_id)
        .order_by(InventoryTransaction.created_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()
