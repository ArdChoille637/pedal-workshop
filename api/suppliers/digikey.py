"""DigiKey adapter (OAuth2 API).

Requires DIGIKEY_CLIENT_ID and DIGIKEY_CLIENT_SECRET.
Docs: https://developer.digikey.com/
"""

import logging

from api.config import settings

logger = logging.getLogger(__name__)


class DigiKeyAdapter:
    slug = "digikey"

    def search(self, query: str) -> list[dict]:
        if not settings.digikey_client_id:
            logger.warning("DigiKey API credentials not configured")
            return []
        # TODO: implement DigiKey Product Search API v4
        return []

    def check_price(self, sku: str) -> dict | None:
        if not settings.digikey_client_id:
            return None
        # TODO: implement DigiKey Product Details API
        return None

    def check_stock(self, sku: str) -> dict | None:
        if not settings.digikey_client_id:
            return None
        return None

    def bulk_check(self, skus: list[str]) -> dict[str, dict]:
        if not settings.digikey_client_id:
            return {}
        return {}
