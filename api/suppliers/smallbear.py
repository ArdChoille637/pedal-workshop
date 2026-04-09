# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
# https://github.com/ArdChoille637/pedal-workshop

"""Small Bear Electronics adapter (web scrape).

Small catalog of specialty pedal components. Weekly poll is sufficient.
"""

import logging

logger = logging.getLogger(__name__)


class SmallBearAdapter:
    slug = "smallbear"

    def search(self, query: str) -> list[dict]:
        # TODO: implement scraping
        return []

    def check_price(self, sku: str) -> dict | None:
        return None

    def check_stock(self, sku: str) -> dict | None:
        return None

    def bulk_check(self, skus: list[str]) -> dict[str, dict]:
        return {}
