# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
# https://github.com/ArdChoille637/pedal-workshop

"""Parse BOM files (CSV/JSON) into structured data for import."""

import csv
import io
import json


def parse_bom_file(content: bytes, filename: str) -> list[dict]:
    """Parse a BOM file and return a list of dicts suitable for creating BOMItem rows."""
    if filename.endswith(".json"):
        return _parse_json(content)
    else:
        return _parse_csv(content)


def _parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    items = []
    for row in reader:
        # Support common CSV column names
        item = {
            "reference": row.get("Reference") or row.get("reference") or row.get("Ref") or row.get("Designator"),
            "category": row.get("Category") or row.get("category") or row.get("Type") or row.get("type") or "other",
            "value": row.get("Value") or row.get("value") or row.get("Part") or "",
            "quantity": int(row.get("Quantity") or row.get("quantity") or row.get("Qty") or row.get("qty") or 1),
            "notes": row.get("Notes") or row.get("notes") or row.get("Description") or row.get("description"),
        }
        if item["value"]:
            items.append(item)

    return items


def _parse_json(content: bytes) -> list[dict]:
    data = json.loads(content)
    if isinstance(data, dict) and "items" in data:
        data = data["items"]

    items = []
    for entry in data:
        item = {
            "reference": entry.get("reference"),
            "category": entry.get("category", "other"),
            "value": entry.get("value", ""),
            "quantity": int(entry.get("quantity", 1)),
            "notes": entry.get("notes"),
        }
        if item["value"]:
            items.append(item)

    return items
