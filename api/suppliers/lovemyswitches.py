# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
# https://github.com/ArdChoille637/pedal-workshop

"""Love My Switches adapter (Shopify JSON).

Shopify-based store, can use /products.json endpoint for catalog access.
"""

import logging

logger = logging.getLogger(__name__)


class LoveMySwitchesAdapter:
    slug = "lovemyswitches"

    def search(self, query: str) -> list[dict]:
        # TODO: query /products.json?q=query
        return []

    def check_price(self, sku: str) -> dict | None:
        return None

    def check_stock(self, sku: str) -> dict | None:
        return None

    def bulk_check(self, skus: list[str]) -> dict[str, dict]:
        return {}
