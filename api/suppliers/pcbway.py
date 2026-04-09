# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
# https://github.com/ArdChoille637/pedal-workshop

"""PCBWay adapter (API/scrape).

PCBWay has a quote API for PCB fabrication. Board pricing depends on specs
(layers, size, quantity, finish). Not a traditional parts supplier.
"""

import logging

logger = logging.getLogger(__name__)


class PCBWayAdapter:
    slug = "pcbway"

    def search(self, query: str) -> list[dict]:
        # PCBWay doesn't have a parts catalog - this is for PCB fab quotes
        return []

    def check_price(self, sku: str) -> dict | None:
        # TODO: implement PCBWay instant quote API
        return None

    def check_stock(self, sku: str) -> dict | None:
        # PCB fab is always available
        return {"in_stock": True, "stock_quantity": None}

    def bulk_check(self, skus: list[str]) -> dict[str, dict]:
        return {}
