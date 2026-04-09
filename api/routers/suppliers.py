from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.supplier import PriceSnapshot, Supplier, SupplierListing
from api.schemas.supplier import (
    PriceSnapshotRead,
    SupplierCreate,
    SupplierListingCreate,
    SupplierListingRead,
    SupplierRead,
)

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierRead])
def list_suppliers(db: Session = Depends(get_db)):
    return db.scalars(select(Supplier).order_by(Supplier.name)).all()


@router.post("", response_model=SupplierRead, status_code=201)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(404, "Supplier not found")
    return supplier


@router.post("/{supplier_id}/poll")
def trigger_poll(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(404, "Supplier not found")
    # TODO: trigger async poll via supplier_poller service
    return {"status": "poll_queued", "supplier": supplier.name}


# --- Supplier Listings ---

@router.get("/{supplier_id}/listings", response_model=list[SupplierListingRead])
def list_listings(supplier_id: int, db: Session = Depends(get_db)):
    stmt = select(SupplierListing).where(SupplierListing.supplier_id == supplier_id)
    return db.scalars(stmt).all()


@router.post("/{supplier_id}/listings", response_model=SupplierListingRead, status_code=201)
def create_listing(supplier_id: int, data: SupplierListingCreate, db: Session = Depends(get_db)):
    listing = SupplierListing(supplier_id=supplier_id, **data.model_dump(exclude={"supplier_id"}))
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


# --- Price History ---

@router.get("/listings/{listing_id}/price-history", response_model=list[PriceSnapshotRead])
def get_price_history(
    listing_id: int,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    stmt = (
        select(PriceSnapshot)
        .where(PriceSnapshot.supplier_listing_id == listing_id)
        .order_by(PriceSnapshot.recorded_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()
