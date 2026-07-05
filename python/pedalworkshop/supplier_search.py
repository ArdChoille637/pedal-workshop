# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Supplier search -- Mouser is the ONLY live searcher.

The Shopify stores (Tayda, Love My Switches, Mammoth) block their public
endpoints and are retired; they exist only as reference suppliers and are never
called here.

Mouser Search API v1:
    POST https://api.mouser.com/api/v1/search/keyword?apiKey=<KEY>
    headers: Content-Type: application/json, Accept: application/json
    body: {"SearchByKeywordRequest": {"keyword": <query>, "records": 8,
           "startingRecord": 0, "searchOptions": "",
           "searchWithYourSignUpLanguage": ""}}
"""

import re
import urllib.parse
from typing import List, Tuple, Optional

from .models import SearchResult

try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:  # pragma: no cover
    requests = None  # type: ignore
    _HAS_REQUESTS = False

MOUSER_ENDPOINT = "https://api.mouser.com/api/v1/search/keyword"
_PRICE_CLEAN = re.compile(r"[^0-9.]")


def _parse_price(raw: str) -> float:
    """Strip everything but digits and dot, e.g. '$0.10' -> 0.10."""
    cleaned = _PRICE_CLEAN.sub("", raw or "")
    # Guard against multiple dots (rare, malformed data).
    if cleaned.count(".") > 1:
        first = cleaned.find(".")
        cleaned = cleaned[: first + 1] + cleaned[first + 1:].replace(".", "")
    try:
        return float(cleaned) if cleaned not in ("", ".") else 0.0
    except ValueError:
        return 0.0


def _parse_availability(raw) -> int:
    """AvailabilityInStock string -> int; 0 if unparseable."""
    if raw is None:
        return 0
    m = re.search(r"\d+", str(raw))
    return int(m.group(0)) if m else 0


def search_mouser(query: str, api_key: str, timeout: float = 15.0) -> List[SearchResult]:
    """Search Mouser by keyword. Returns [] on any non-200 / error / no key.

    Raises RuntimeError if `requests` is not installed (surfaced by search_all
    as a failure note).
    """
    if not _HAS_REQUESTS:
        raise RuntimeError("The 'requests' package is not installed.")
    if not query or not api_key:
        return []

    url = MOUSER_ENDPOINT + "?apiKey=" + urllib.parse.quote(api_key)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    body = {
        "SearchByKeywordRequest": {
            "keyword": query,
            "records": 8,
            "startingRecord": 0,
            "searchOptions": "",
            "searchWithYourSignUpLanguage": "",
        }
    }

    resp = requests.post(url, json=body, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        # Non-200 -> no results (caller reports a failure note).
        return []

    data = resp.json()
    parts = ((data or {}).get("SearchResults") or {}).get("Parts") or []
    results: List[SearchResult] = []
    for part in parts:
        mpn = part.get("ManufacturerPartNumber") or ""
        mouser_pn = part.get("MouserPartNumber") or ""
        description = part.get("Description") or ""
        availability = _parse_availability(part.get("AvailabilityInStock"))

        breaks = part.get("PriceBreaks") or []
        price = 0.0
        if breaks:
            chosen = None
            for b in breaks:
                if int(b.get("Quantity", 0) or 0) == 1:
                    chosen = b
                    break
            if chosen is None:
                chosen = breaks[0]
            price = _parse_price(chosen.get("Price", ""))

        url_detail: Optional[str] = None
        if mouser_pn:
            url_detail = "https://www.mouser.com/ProductDetail/" + urllib.parse.quote(mouser_pn)

        results.append(SearchResult(
            supplier_slug="mouser",
            supplier_name="Mouser",
            sku=mouser_pn,
            title=description or mpn,
            price=price,
            currency="USD",
            in_stock=availability > 0,
            url=url_detail,
        ))
    return results


def search_all(
    query: str, mouser_key: Optional[str]
) -> Tuple[List[SearchResult], List[str]]:
    """Run all live searchers (Mouser only).

    Returns (results, failures) where `failures` is a list of human-readable
    notes describing searchers that could not run.
    """
    results: List[SearchResult] = []
    failures: List[str] = []

    if not mouser_key:
        failures.append("Mouser: no API key set (add one in Settings -- free at mouser.com/api-hub).")
        return results, failures

    try:
        results.extend(search_mouser(query, mouser_key))
    except Exception as exc:  # network error, missing requests, bad JSON, etc.
        failures.append("Mouser: search failed ({}).".format(exc))

    return results, failures
