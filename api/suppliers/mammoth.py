"""Mammoth Electronics adapter (Shopify JSON).

Shopify-based store, can use /products.json endpoint for catalog access.
"""

import logging

logger = logging.getLogger(__name__)


class MammothAdapter:
    slug = "mammoth"

    def search(self, query: str) -> list[dict]:
        # TODO: query /products.json?q=query
        return []

    def check_price(self, sku: str) -> dict | None:
        return None

    def check_stock(self, sku: str) -> dict | None:
        return None

    def bulk_check(self, skus: list[str]) -> dict[str, dict]:
        return {}
