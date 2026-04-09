"""Base protocol for supplier adapters."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SupplierAdapter(Protocol):
    slug: str

    def search(self, query: str) -> list[dict]:
        """Search supplier catalog. Returns list of {sku, name, price, in_stock, url}."""
        ...

    def check_price(self, sku: str) -> dict | None:
        """Check price for a single SKU. Returns {price, currency} or None."""
        ...

    def check_stock(self, sku: str) -> dict | None:
        """Check stock for a single SKU. Returns {in_stock, stock_quantity} or None."""
        ...

    def bulk_check(self, skus: list[str]) -> dict[str, dict]:
        """Check price and stock for multiple SKUs.
        Returns {sku: {price, in_stock, stock_quantity}}."""
        ...
