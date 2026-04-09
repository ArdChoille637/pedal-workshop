# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
# https://github.com/ArdChoille637/pedal-workshop

"""
Tayda Electronics supplier adapter.

Tayda runs on Shopify, which exposes a public ``/products.json`` endpoint —
no API key required.  The same pattern applies to Mammoth Electronics and
Love My Switches (see the Swift ``ShopifySearcher`` actor for the native
implementation).

IMPLEMENTATION GUIDE
--------------------
The methods below are stubs.  Here's exactly how to implement each one.

``search(query)``
~~~~~~~~~~~~~~~~~
::

    import requests, time

    BASE = "https://www.taydaelectronics.com"
    RATE_DELAY = 1.0  # seconds between requests — be polite

    def search(self, query: str) -> list[SupplierResult]:
        url = f"{BASE}/products.json"
        params = {"q": query, "limit": 10}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        results = []
        for product in resp.json().get("products", []):
            for variant in product["variants"][:1]:   # first variant only
                results.append(SupplierResult(
                    sku      = variant.get("sku") or str(variant["id"]),
                    title    = product["title"],
                    price    = float(variant["price"]),
                    in_stock = variant.get("available", False),
                    url      = f"{BASE}/products/{product['handle']}",
                ))
        time.sleep(RATE_DELAY)
        return results

``check_price(sku)`` / ``check_stock(sku)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tayda's Shopify doesn't offer direct SKU lookup via the public API.
Options:
  a) Search by SKU string and filter results.
  b) Scrape the product page (fragile, use with caution).
  c) Use Tayda's internal search and match on SKU field.

``bulk_check(skus)``
~~~~~~~~~~~~~~~~~~~~
Loop over SKUs with rate limiting.  Tayda doesn't have a batch API.
::

    def bulk_check(self, skus: list[str]) -> dict[str, SupplierResult]:
        results = {}
        for sku in skus:
            hit = self.check_price(sku)
            if hit:
                results[sku] = hit
            time.sleep(self.RATE_DELAY)
        return results

RATE LIMITING
-------------
Tayda's Shopify is fairly permissive but 1 req/s is safe for bulk ops.
For production use, wrap requests with ``tenacity`` retry + exponential backoff::

    from tenacity import retry, stop_after_attempt, wait_exponential

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def _get(self, url, **kwargs):
        return requests.get(url, **kwargs)
"""

import logging
import time

from .base import SupplierAdapter, SupplierResult

logger = logging.getLogger(__name__)

# Shopify storefront base URL.  Change this to point to a different Shopify store.
_BASE_URL = "https://www.taydaelectronics.com"

# Minimum delay between outbound requests (seconds).
# Increase if you get 429 Too Many Requests responses.
_RATE_DELAY_S = 1.0


class TaydaAdapter:
    """
    Tayda Electronics — Shopify-based, no API key required.

    See module docstring for implementation guide.
    """

    slug = "tayda"

    def search(self, query: str) -> list[SupplierResult]:
        """
        Search Tayda's public Shopify catalog.

        TODO: implement using the pattern in the module docstring.
        Returns an empty list until implemented — the app degrades gracefully.
        """
        logger.info("TaydaAdapter.search not yet implemented (query=%r)", query)
        return []

    def check_price(self, sku: str) -> SupplierResult | None:
        """
        Look up current price for a single Tayda SKU.

        TODO: implement via search + SKU filter or product page scrape.
        """
        logger.debug("TaydaAdapter.check_price not yet implemented (sku=%r)", sku)
        return None

    def check_stock(self, sku: str) -> SupplierResult | None:
        """
        Look up stock availability for a single Tayda SKU.

        TODO: same approach as check_price — availability is in the variant object.
        """
        logger.debug("TaydaAdapter.check_stock not yet implemented (sku=%r)", sku)
        return None

    def bulk_check(self, skus: list[str]) -> dict[str, SupplierResult]:
        """
        Check price + stock for multiple Tayda SKUs.

        TODO: loop check_price() with _RATE_DELAY_S between requests.
        """
        logger.debug("TaydaAdapter.bulk_check not yet implemented (%d skus)", len(skus))
        return {}
