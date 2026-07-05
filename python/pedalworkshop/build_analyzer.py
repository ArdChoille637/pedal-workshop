# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Build Analyzer -- readiness-tier classification.

This is a straight port of ``BuildAnalyzer`` from the native macOS app
(WorkshopCore/Services). It runs entirely in-memory; no network calls.

Matching is done against a StockKey = (normalize_value(category),
normalize_value(value)) so minor formatting differences (e.g. "10K Ohm" vs
"10k") do not create false "missing" results.

Tiers (by count of missing parts):
    0        -> Ready
    1..3     -> ARNA 1-3
    4+       -> ARNA 4+

The missing-part count EXCLUDES optional BOM rows and the enclosure -- both are
sourced separately and do not gate build readiness.
"""

import re
from typing import List, Dict, Tuple

from .models import (
    Component,
    Project,
    BOMItem,
    MissingPart,
    ProjectBuildStatus,
    BuildTiers,
    DashboardSummary,
)

# Pre-compiled regexes mirroring the Swift NSRegularExpression patterns.
_RE_OHMS = re.compile(r"\s*ohms?\b")
_RE_EURO_SHORTHAND = re.compile(r"^(\d+)([kmunpf])(\d+)$")
_RE_STRAY_R = re.compile(r"([kmunpfhva])r$")
_RE_BARE_R = re.compile(r"^(\d+(?:\.\d+)?)r$")


def normalize_value(raw: str) -> str:
    """Canonicalise a component value string.

    Transformations (in order), identical to the Swift implementation:
      1. trim whitespace; lowercase.
      2. replace unicode ohm signs (U+2126, U+03C9, U+03A9) with "ohm".
      3. remove ``\\s*ohms?\\b``.
      4. European shorthand ``^(\\d+)([kmunpf])(\\d+)$`` -> ``\\1.\\3\\2``
         (e.g. "4k7" -> "4.7k").
      5. ``([kmunpfhva])r$`` -> ``\\1`` (strip stray trailing r after a multiplier).
      6. ``^(\\d+(?:\\.\\d+)?)r$`` -> ``\\1`` (bare "470r" -> "470").
    """
    s = (raw or "").strip().lower()

    # 2. Unicode ohm signs -> the word "ohm" (so the ohm-stripper catches them).
    s = s.replace("Ω", "ohm")  # OHM SIGN
    s = s.replace("ω", "ohm")  # greek small omega
    s = s.replace("Ω", "ohm")  # greek capital omega

    # 3. Remove " ohms" / " ohm" (with optional preceding space).
    s = _RE_OHMS.sub("", s)

    # 4. European embedded-multiplier shorthand: "4k7" -> "4.7k".
    s = _RE_EURO_SHORTHAND.sub(r"\1.\3\2", s)

    # 5. Strip a stray trailing "r" after a multiplier suffix ("4.7kr" -> "4.7k").
    s = _RE_STRAY_R.sub(r"\1", s)

    # 6. Bare trailing "r" on a plain number is resistor shorthand ("470r" -> "470").
    s = _RE_BARE_R.sub(r"\1", s)

    return s


def _stock_key(category: str, value: str) -> Tuple[str, str]:
    return (normalize_value(category), normalize_value(value))


def analyze(
    projects: List[Project],
    bom_items: List[BOMItem],
    components: List[Component],
) -> BuildTiers:
    """Classify every project into a readiness tier."""
    # Build a normalised stock lookup: stock[key] += quantity.
    stock: Dict[Tuple[str, str], int] = {}
    for c in components:
        key = _stock_key(c.category, c.value)
        stock[key] = stock.get(key, 0) + c.quantity

    ready: List[ProjectBuildStatus] = []
    arna13: List[ProjectBuildStatus] = []
    arna4plus: List[ProjectBuildStatus] = []

    for project in projects:
        bom = [b for b in bom_items if b.project_id == project.id]
        # Projects with no BOM rows cannot be classified -- skip.
        if not bom:
            continue

        # Optional rows never demote a build; the enclosure is excluded from the
        # missing-part (ARNA) count. Aggregate remaining demand per StockKey so
        # duplicate BOM lines can't each claim the full on-hand quantity.
        required = [
            item
            for item in bom
            if item.is_optional == 0
            and item.category.strip().lower() != "enclosure"
        ]

        demand: Dict[Tuple[str, str], int] = {}
        representative: Dict[Tuple[str, str], BOMItem] = {}
        for item in required:
            key = _stock_key(item.category, item.value)
            demand[key] = demand.get(key, 0) + item.quantity
            if key not in representative:
                representative[key] = item

        missing: List[MissingPart] = []
        # Stable iteration order (by category then value) so chips don't shuffle.
        for key in sorted(demand.keys()):
            needed = demand[key]
            item = representative.get(key)
            if item is None:
                continue
            on_hand = stock.get(key, 0)
            shortfall = max(0, needed - on_hand)
            if shortfall <= 0:
                continue
            missing.append(
                MissingPart(
                    bom_item_id=item.id,
                    reference=item.reference,
                    category=item.category,
                    value=item.value,
                    shortfall=shortfall,
                )
            )

        status = ProjectBuildStatus(
            project_id=project.id,
            project_name=project.name,
            effect_type=project.effect_type,
            status=project.status,
            bom_count=len(bom),
            missing_count=len(missing),
            missing_parts=missing,
        )

        # Tier assignment. Ready/ARNA boundary is fixed at 0; the ARNA 1-3 / 4+
        # boundary is the upper bound of the 1..3 range.
        n = len(missing)
        if n == 0:
            ready.append(status)
        elif 1 <= n <= 3:
            arna13.append(status)
        else:
            arna4plus.append(status)

    return BuildTiers(ready=ready, arna13=arna13, arna4plus=arna4plus)


def summary(
    components: List[Component],
    projects: List[Project],
    tiers: BuildTiers,
) -> DashboardSummary:
    """Derive a flat DashboardSummary from already-computed tiers."""
    total = sum(c.quantity for c in components)
    low_stock = sum(1 for c in components if c.is_low_stock)
    active_statuses = {"prototype", "production"}
    active = sum(1 for p in projects if p.status in active_statuses)
    return DashboardSummary(
        total_components=total,
        total_unique_parts=len(components),
        total_projects=len(projects),
        active_builds=active,
        low_stock_count=low_stock,
        ready_count=len(tiers.ready),
        arna13_count=len(tiers.arna13),
        arna4plus_count=len(tiers.arna4plus),
    )
