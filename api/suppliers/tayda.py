"""Tayda Electronics adapter (web scrape).

Tayda has no public API. Prices are very stable so daily polls suffice.
Rate limited to 1 request per 2 seconds.
"""

import logging

logger = logging.getLogger(__name__)


class TaydaAdapter:
    slug = "tayda"

    def search(self, query: str) -> list[dict]:
        # TODO: implement scraping of tayda search results
        logger.info(f"Tayda search not yet implemented: {query}")
        return []

    def check_price(self, sku: str) -> dict | None:
        # TODO: scrape product page for price
        return None

    def check_stock(self, sku: str) -> dict | None:
        # TODO: scrape product page for stock status
        return None

    def bulk_check(self, skus: list[str]) -> dict[str, dict]:
        # TODO: iterate SKUs with rate limiting
        return {}
