# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
# https://github.com/ArdChoille637/pedal-workshop

"""
Supplier adapter protocol and shared result type.

PURPOSE
-------
Every supplier adapter must satisfy the ``SupplierAdapter`` Protocol defined
here.  The protocol is ``@runtime_checkable`` so you can do
``isinstance(adapter, SupplierAdapter)`` in tests.

TO ADD A NEW SUPPLIER
---------------------
1.  Create ``api/suppliers/<slug>.py`` (copy tayda.py as a starting point).
2.  Implement all four methods below — return empty/None for any not supported.
3.  Register the adapter in ``api/suppliers/__init__.py`` and in the seed data
    (``seeds/suppliers.json`` / ``native/Sources/WorkshopCore/Resources/suppliers.json``).
4.  For Shopify stores the Swift side is handled automatically by adding a new
    ``ShopifySearcher`` instance in ``SupplierSearch.swift``.

RATE LIMITING
-------------
Most supplier sites will block you if you hammer them.  Use the ``_rate_limit``
helper or ``tenacity`` retry + sleep between requests.  Tayda's Shopify endpoint
is fairly permissive; Mouser's REST API has a documented rate limit.

RETURN TYPE
-----------
All methods return ``SupplierResult`` dicts or lists thereof so callers don't
need to know supplier-specific field names.  The schema is documented on
``SupplierResult`` below.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Shared result type
# ---------------------------------------------------------------------------

@dataclass
class SupplierResult:
    """
    Normalised representation of a single product listing from any supplier.

    Fields
    ------
    sku :
        Supplier's own part number / SKU.  May differ from the manufacturer
        part number (``mpn``).
    title :
        Human-readable product title as returned by the supplier.
    price :
        Unit price in ``currency`` (default USD).  ``None`` if unknown.
    currency :
        ISO 4217 currency code.  Defaults to "USD".
    in_stock :
        ``True`` if the supplier reports availability > 0.
    stock_qty :
        Reported stock quantity.  ``None`` if the supplier doesn't expose it.
    url :
        Direct product page URL, or ``None``.
    mpn :
        Manufacturer part number if the supplier exposes it, else ``None``.
    """

    sku:       str
    title:     str
    price:     float | None = None
    currency:  str = "USD"
    in_stock:  bool = False
    stock_qty: int | None = None
    url:       str | None = None
    mpn:       str | None = None

    def to_dict(self) -> dict:
        """Serialise to a plain dict for JSON responses."""
        return {
            "sku":       self.sku,
            "title":     self.title,
            "price":     self.price,
            "currency":  self.currency,
            "in_stock":  self.in_stock,
            "stock_qty": self.stock_qty,
            "url":       self.url,
            "mpn":       self.mpn,
        }


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class SupplierAdapter(Protocol):
    """
    Structural protocol every supplier adapter must satisfy.

    Implementing this protocol is enough — you do NOT need to inherit from a
    base class.  Duck typing is used at the call sites.

    Attributes
    ----------
    slug :
        Short identifier used in database records and URL paths (e.g. "tayda").
        Must match the ``slug`` field in the suppliers seed JSON.
    """

    slug: str

    def search(self, query: str) -> list[SupplierResult]:
        """
        Search the supplier's catalog for ``query``.

        Parameters
        ----------
        query :
            Free-text search term, e.g. "10k resistor 1/4w".

        Returns
        -------
        list[SupplierResult]
            Up to ~10 results sorted by relevance (supplier's own ordering).
            Return an empty list rather than raising on a network error; log
            the exception instead so the caller degrades gracefully.
        """
        ...

    def check_price(self, sku: str) -> SupplierResult | None:
        """
        Look up the current price for a single SKU.

        Returns ``None`` if the SKU is not found or the request fails.
        """
        ...

    def check_stock(self, sku: str) -> SupplierResult | None:
        """
        Look up stock availability for a single SKU.

        Returns ``None`` if unavailable.
        """
        ...

    def bulk_check(self, skus: list[str]) -> dict[str, SupplierResult]:
        """
        Check price and stock for multiple SKUs in one operation.

        Returns a dict keyed by SKU.  Missing SKUs are omitted.
        Prefer this over calling ``check_price`` in a loop — most APIs
        support batch requests and it's much kinder to their servers.
        """
        ...
