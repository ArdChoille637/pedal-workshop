# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
# https://github.com/ArdChoille637/pedal-workshop

"""Core build readiness analyzer.

Classifies all active projects into three tiers:
- Ready to Build: all required BOM items satisfied by on-hand inventory
- ARNA 1-3: 1-3 parts short of buildable
- ARNA 4+: 4+ parts short of buildable

For ARNA projects, identifies exactly which parts are missing and finds
the cheapest supplier source for each.
"""

from collections import defaultdict

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from api.models.component import Component
from api.models.project import BOMItem, Project
from api.models.supplier import SupplierListing, Supplier
from api.schemas.dashboard import (
    CheapestSource,
    DashboardResponse,
    MissingPart,
    ProjectBuildStatus,
)

ACTIVE_STATUSES = ("design", "prototype", "production")


def analyze_build_tiers(db: Session) -> DashboardResponse:
    # Single-pass query: join BOM items against inventory
    stmt = text("""
        SELECT
            p.id AS project_id,
            p.name AS project_name,
            p.effect_type,
            p.status,
            bi.id AS bom_item_id,
            bi.reference,
            bi.category,
            bi.value,
            bi.quantity AS needed,
            COALESCE(c.quantity, 0) AS in_stock,
            bi.component_id,
            CASE
                WHEN bi.component_id IS NULL THEN bi.quantity
                WHEN c.quantity < bi.quantity THEN bi.quantity - c.quantity
                ELSE 0
            END AS shortfall
        FROM projects p
        JOIN bom_items bi ON bi.project_id = p.id AND bi.is_optional = 0
        LEFT JOIN components c ON bi.component_id = c.id
        WHERE p.status IN ('design', 'prototype', 'production')
        ORDER BY p.id, bi.id
    """)

    rows = db.execute(stmt).mappings().all()

    # Group by project
    projects: dict[int, dict] = {}
    project_missing: dict[int, list[MissingPart]] = defaultdict(list)

    for row in rows:
        pid = row["project_id"]
        if pid not in projects:
            projects[pid] = {
                "project_id": pid,
                "project_name": row["project_name"],
                "effect_type": row["effect_type"],
                "status": row["status"],
                "bom_count": 0,
            }
        projects[pid]["bom_count"] += 1

        if row["shortfall"] > 0:
            project_missing[pid].append(
                MissingPart(
                    bom_item_id=row["bom_item_id"],
                    reference=row["reference"],
                    category=row["category"],
                    value=row["value"],
                    shortfall=row["shortfall"],
                )
            )

    # Also include projects with no BOM items (they show as ready with 0 items)
    no_bom_projects = db.scalars(
        select(Project).where(
            Project.status.in_(ACTIVE_STATUSES),
            ~Project.id.in_(projects.keys()) if projects else True,
        )
    ).all()
    for p in no_bom_projects:
        if p.id not in projects:
            projects[p.id] = {
                "project_id": p.id,
                "project_name": p.name,
                "effect_type": p.effect_type,
                "status": p.status,
                "bom_count": 0,
            }

    # Find cheapest supplier for missing parts
    _enrich_missing_with_suppliers(db, project_missing)

    # Classify into tiers
    ready = []
    arna_1_3 = []
    arna_4_plus = []

    for pid, info in projects.items():
        missing = project_missing.get(pid, [])
        missing_count = len(missing)
        estimated_cost = sum(
            (mp.cheapest_source.price or 0) * mp.shortfall
            for mp in missing
            if mp.cheapest_source and mp.cheapest_source.price
        ) or None

        status = ProjectBuildStatus(
            missing_count=missing_count,
            missing_parts=missing,
            estimated_cost=estimated_cost,
            **info,
        )

        if missing_count == 0:
            ready.append(status)
        elif missing_count <= 3:
            arna_1_3.append(status)
        else:
            arna_4_plus.append(status)

    # Sort: ready by name, ARNA by missing count ascending
    ready.sort(key=lambda x: x.project_name)
    arna_1_3.sort(key=lambda x: x.missing_count)
    arna_4_plus.sort(key=lambda x: x.missing_count)

    return DashboardResponse(ready=ready, arna_1_3=arna_1_3, arna_4_plus=arna_4_plus)


def _enrich_missing_with_suppliers(db: Session, project_missing: dict[int, list[MissingPart]]):
    """For each missing part, find the cheapest in-stock supplier listing."""
    # Collect all component values we need to look up
    all_missing = [mp for parts in project_missing.values() for mp in parts]
    if not all_missing:
        return

    # Get all supplier listings with their supplier names, grouped by component value + category
    stmt = (
        select(SupplierListing, Supplier.name.label("supplier_name"), Component.value, Component.category)
        .join(Supplier, SupplierListing.supplier_id == Supplier.id)
        .join(Component, SupplierListing.component_id == Component.id)
        .where(SupplierListing.in_stock == 1)
        .order_by(SupplierListing.unit_price)
    )
    results = db.execute(stmt).all()

    # Index by (category, value) -> cheapest listing
    cheapest: dict[tuple[str, str], CheapestSource] = {}
    for listing, supplier_name, comp_value, comp_category in results:
        key = (comp_category, comp_value)
        if key not in cheapest:
            cheapest[key] = CheapestSource(
                supplier=supplier_name,
                price=listing.unit_price,
                in_stock=True,
            )

    for mp in all_missing:
        source = cheapest.get((mp.category, mp.value))
        if source:
            mp.cheapest_source = source
