# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
# https://github.com/ArdChoille637/pedal-workshop

"""Mouser Electronics adapter (REST API).

Requires MOUSER_API_KEY. Free tier: 1000 requests/day.
Docs: https://api.mouser.com/api/docs/ui/index
"""

import logging

from api.config import settings

logger = logging.getLogger(__name__)


class MouserAdapter:
    slug = "mouser"

    def search(self, query: str) -> list[dict]:
        if not settings.mouser_api_key:
            logger.warning("Mouser API key not configured")
            return []
        # TODO: implement Mouser SearchByKeyword API
        return []

    def check_price(self, sku: str) -> dict | None:
        if not settings.mouser_api_key:
            return None
        # TODO: implement Mouser SearchByPartNumber API
        return None

    def check_stock(self, sku: str) -> dict | None:
        if not settings.mouser_api_key:
            return None
        # TODO: implement Mouser SearchByPartNumber API
        return None

    def bulk_check(self, skus: list[str]) -> dict[str, dict]:
        if not settings.mouser_api_key:
            return {}
        # TODO: batch queries with rate limiting
        return {}
