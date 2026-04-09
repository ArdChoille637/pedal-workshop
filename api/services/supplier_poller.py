"""Background supplier polling orchestration.

Iterates through enabled suppliers, calls their adapter's bulk_check,
updates supplier_listings and records price_snapshots.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models.supplier import PriceSnapshot, Supplier, SupplierListing

logger = logging.getLogger(__name__)


def poll_all_suppliers():
    """Synchronous entry point called by APScheduler."""
    db = SessionLocal()
    try:
        suppliers = db.scalars(
            select(Supplier).where(Supplier.poll_enabled == 1)
        ).all()

        for supplier in suppliers:
            try:
                _poll_supplier(db, supplier)
            except Exception:
                logger.exception(f"Failed to poll supplier: {supplier.name}")

    finally:
        db.close()


def _poll_supplier(db: Session, supplier: Supplier):
    """Poll a single supplier for all tracked listings."""
    from api.suppliers import get_adapter

    adapter = get_adapter(supplier.slug)
    if adapter is None:
        logger.warning(f"No adapter for supplier: {supplier.slug}")
        return

    listings = db.scalars(
        select(SupplierListing).where(SupplierListing.supplier_id == supplier.id)
    ).all()

    if not listings:
        return

    skus = [listing.sku for listing in listings]
    results = adapter.bulk_check(skus)

    now = datetime.now(timezone.utc)
    for listing in listings:
        result = results.get(listing.sku)
        if result is None:
            continue

        listing.unit_price = result.get("price")
        listing.in_stock = 1 if result.get("in_stock") else 0
        listing.stock_quantity = result.get("stock_quantity")
        listing.last_checked_at = now

        snapshot = PriceSnapshot(
            supplier_listing_id=listing.id,
            unit_price=result.get("price", 0),
            in_stock=listing.in_stock,
            stock_quantity=listing.stock_quantity,
        )
        db.add(snapshot)

    supplier.last_polled_at = now
    db.commit()
    logger.info(f"Polled {supplier.name}: updated {len(results)} of {len(listings)} listings")
