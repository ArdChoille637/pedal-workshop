# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Data models for Pedal Workshop.

Every persisted model is a plain dataclass with ``from_dict`` / ``to_dict``
helpers.  JSON keys are snake_case (matching the native macOS app's CodingKeys
and the shared seed files), while the Python attributes are also snake_case,
so the mapping is 1:1 except for a couple of defensive defaults.

Portability note: we intentionally use ``typing.Optional[...]`` rather than the
3.10-only ``X | None`` syntax, and avoid ``match`` statements, so the module
imports cleanly on Python 3.8+.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------------------------
# Component
# ---------------------------------------------------------------------------
@dataclass
class Component:
    id: int
    category: str
    value: str
    quantity: int = 0
    min_quantity: int = 0
    subcategory: Optional[str] = None
    value_numeric: Optional[float] = None
    value_unit: Optional[str] = None
    package: Optional[str] = None
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    mpn: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    @property
    def is_low_stock(self) -> bool:
        """Matches the Swift rule: min_quantity > 0 and quantity < min_quantity."""
        return self.min_quantity > 0 and self.quantity < self.min_quantity

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Component":
        return cls(
            id=int(d["id"]),
            category=d.get("category", ""),
            value=d.get("value", ""),
            quantity=int(d.get("quantity", 0) or 0),
            min_quantity=int(d.get("min_quantity", 0) or 0),
            subcategory=d.get("subcategory"),
            value_numeric=d.get("value_numeric"),
            value_unit=d.get("value_unit"),
            package=d.get("package"),
            description=d.get("description"),
            manufacturer=d.get("manufacturer"),
            mpn=d.get("mpn"),
            location=d.get("location"),
            notes=d.get("notes"),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
@dataclass
class Project:
    id: int
    name: str
    slug: str
    status: str = "design"
    effect_type: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    schematic_id: Optional[int] = None
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Project":
        return cls(
            id=int(d["id"]),
            name=d.get("name", ""),
            slug=d.get("slug", ""),
            status=d.get("status", "design"),
            effect_type=d.get("effect_type"),
            description=d.get("description"),
            notes=d.get("notes"),
            schematic_id=d.get("schematic_id"),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# BOMItem
# ---------------------------------------------------------------------------
@dataclass
class BOMItem:
    id: int
    project_id: int
    category: str
    value: str
    quantity: int = 1
    component_id: Optional[int] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    is_optional: int = 0  # 0/1
    created_at: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BOMItem":
        return cls(
            id=int(d["id"]),
            project_id=int(d["project_id"]),
            category=d.get("category", ""),
            value=d.get("value", ""),
            quantity=int(d.get("quantity", 1) or 1),
            component_id=d.get("component_id"),
            reference=d.get("reference"),
            notes=d.get("notes"),
            is_optional=int(d.get("is_optional", 0) or 0),
            created_at=d.get("created_at", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------
@dataclass
class Supplier:
    id: int
    name: str
    slug: str
    api_type: str = "manual"
    website: Optional[str] = None
    poll_enabled: int = 0
    poll_interval: int = 0
    last_polled_at: Optional[str] = None
    created_at: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Supplier":
        return cls(
            id=int(d["id"]),
            name=d.get("name", ""),
            slug=d.get("slug", ""),
            api_type=d.get("api_type", "manual"),
            website=d.get("website"),
            poll_enabled=int(d.get("poll_enabled", 0) or 0),
            poll_interval=int(d.get("poll_interval", 0) or 0),
            last_polled_at=d.get("last_polled_at"),
            created_at=d.get("created_at", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# SupplierListing
# ---------------------------------------------------------------------------
@dataclass
class SupplierListing:
    id: int
    supplier_id: int
    sku: str
    title: str
    price: float
    currency: str = "USD"
    in_stock: bool = False
    component_id: Optional[int] = None
    url: Optional[str] = None
    last_checked: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SupplierListing":
        return cls(
            id=int(d["id"]),
            supplier_id=int(d["supplier_id"]),
            sku=d.get("sku", ""),
            title=d.get("title", ""),
            price=float(d.get("price", 0.0) or 0.0),
            currency=d.get("currency", "USD"),
            in_stock=bool(d.get("in_stock", False)),
            component_id=d.get("component_id"),
            url=d.get("url"),
            last_checked=d.get("last_checked", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Schematic
# ---------------------------------------------------------------------------
@dataclass
class Schematic:
    id: int
    category_folder: str
    file_name: str
    file_path: str
    file_type: str
    file_size: Optional[int] = None
    effect_type: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Schematic":
        return cls(
            id=int(d["id"]),
            category_folder=d.get("category_folder", ""),
            file_name=d.get("file_name", ""),
            file_path=d.get("file_path", ""),
            file_type=d.get("file_type", ""),
            file_size=d.get("file_size"),
            effect_type=d.get("effect_type"),
            tags=d.get("tags"),
            created_at=d.get("created_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Transient / computed models (NOT persisted)
# ---------------------------------------------------------------------------
@dataclass
class SearchResult:
    """A transient supplier search hit (e.g. a Mouser Parts[] entry)."""
    supplier_slug: str
    supplier_name: str
    sku: str
    title: str
    price: float
    currency: str = "USD"
    in_stock: bool = False
    url: Optional[str] = None


@dataclass
class MissingPart:
    reference: Optional[str]
    category: str
    value: str
    shortfall: int
    bom_item_id: Optional[int] = None


@dataclass
class ProjectBuildStatus:
    project_id: int
    project_name: str
    effect_type: Optional[str]
    status: str
    bom_count: int
    missing_count: int
    missing_parts: List[MissingPart] = field(default_factory=list)


@dataclass
class BuildTiers:
    ready: List[ProjectBuildStatus] = field(default_factory=list)
    arna13: List[ProjectBuildStatus] = field(default_factory=list)
    arna4plus: List[ProjectBuildStatus] = field(default_factory=list)


@dataclass
class DashboardSummary:
    total_components: int = 0
    total_unique_parts: int = 0
    total_projects: int = 0
    active_builds: int = 0
    low_stock_count: int = 0
    ready_count: int = 0
    arna13_count: int = 0
    arna4plus_count: int = 0
