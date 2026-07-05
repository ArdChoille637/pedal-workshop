# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Local JSON storage for Pedal Workshop.

Mirrors the native app's LocalDataStore: each collection is a JSON file in a
per-user data directory. On first run the writable collections are seeded from
the bundled seed JSONs (pedalworkshop/seeds/). Auto-increment integer ids.

Collections / files:
    components.json        (seeded from common_components.json)
    suppliers.json         (seeded from suppliers.json)
    projects.json          (seeded from sample_project.json)
    bom_items.json         (seeded from sample_project.json's "bom")
    supplier_listings.json (starts empty)
    schematics.json        (starts empty; populated by folder picker)
    settings.json          (key/value; e.g. schematics_folder)

Mouser API key: stored in the OS keyring via the `keyring` package if it is
importable; otherwise it falls back to settings.json.
    TRADEOFF: keyring keeps the secret out of a plaintext, world-readable file
    and out of backups of the data dir. The settings.json fallback is
    convenient and portable but stores the key in cleartext -- acceptable for a
    single-user desktop tool, but the keyring path is preferred when available.
"""

import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .models import (
    Component,
    Project,
    BOMItem,
    Supplier,
    SupplierListing,
    Schematic,
)

# ---------------------------------------------------------------------------
# Optional secure key storage.
# ---------------------------------------------------------------------------
try:
    import keyring  # type: ignore
    _HAS_KEYRING = True
except Exception:  # pragma: no cover - environment dependent
    keyring = None  # type: ignore
    _HAS_KEYRING = False

_KEYRING_SERVICE = "PedalWorkshop"
_MOUSER_KEY_NAME = "mouser_api_key"

_SEEDS_DIR = Path(__file__).resolve().parent / "seeds"


def _now_iso() -> str:
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def default_data_dir() -> Path:
    """Per-user data directory (~/.pedalworkshop by default).

    Kept dependency-free (no appdirs) for portability; the location is shown to
    the user in Settings.
    """
    return Path.home() / ".pedalworkshop"


class Store:
    """JSON-file-backed data store with CRUD for each collection."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._seed_if_needed()

    # ------------------------------------------------------------------ paths
    def _path(self, name: str) -> Path:
        return self.data_dir / f"{name}.json"

    def _read_raw(self, name: str, default: Any) -> Any:
        p = self._path(name)
        if not p.exists():
            return default
        try:
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # Corrupt file -> quarantine and fall back to default.
            try:
                p.rename(p.with_suffix(".json.corrupt"))
            except Exception:
                pass
            return default

    def _write_raw(self, name: str, data: Any) -> None:
        p = self._path(name)
        tmp = p.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        tmp.replace(p)  # atomic on same filesystem

    # ------------------------------------------------------------------ seed
    def _load_seed(self, filename: str, default: Any) -> Any:
        p = _SEEDS_DIR / filename
        if not p.exists():
            return default
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _slugify(name: str) -> str:
        out = []
        prev_dash = False
        for ch in name.lower():
            if ch.isalnum():
                out.append(ch)
                prev_dash = False
            else:
                if not prev_dash and out:
                    out.append("-")
                    prev_dash = True
        return "".join(out).strip("-")

    def _seed_if_needed(self) -> None:
        """Seed writable collections on first run.

        Seed shapes are the terse shared seed JSONs, so we synthesise the fields
        the models need but the seeds omit (id, quantity, timestamps, slug).
        """
        ts = "2025-01-01T00:00:00"

        # --- components ---
        if not self._path("components").exists():
            raw = self._load_seed("common_components.json", [])
            comps: List[Dict[str, Any]] = []
            for i, c in enumerate(raw, start=1):
                d = dict(c)
                d["id"] = i
                # Seeds have no stock levels; give a sensible default so the
                # dashboard has data. min_quantity=5 marks a low-stock line when
                # quantity dips below it. (Documented seeding choice.)
                d.setdefault("quantity", 5)
                d.setdefault("min_quantity", 5)
                d.setdefault("created_at", ts)
                d.setdefault("updated_at", ts)
                comps.append(d)
            self._write_raw("components", comps)

        # --- suppliers ---
        if not self._path("suppliers").exists():
            raw = self._load_seed("suppliers.json", [])
            sups: List[Dict[str, Any]] = []
            for i, s in enumerate(raw, start=1):
                d = dict(s)
                d["id"] = i
                d.setdefault("poll_enabled", 0)
                d.setdefault("poll_interval", d.get("poll_interval", 0))
                d.setdefault("last_polled_at", None)
                d.setdefault("created_at", ts)
                sups.append(d)
            self._write_raw("suppliers", sups)

        # --- projects + bom_items (from the combined sample_project seed) ---
        if not self._path("projects").exists() and not self._path("bom_items").exists():
            raw = self._load_seed("sample_project.json", {})
            projects: List[Dict[str, Any]] = []
            bom_items: List[Dict[str, Any]] = []
            # The seed may be a single project object or a list of them.
            seed_projects = raw if isinstance(raw, list) else [raw]
            pid = 0
            bid = 0
            for proj in seed_projects:
                if not proj:
                    continue
                pid += 1
                slug = proj.get("slug") or self._slugify(proj.get("name", "project"))
                projects.append({
                    "id": pid,
                    "name": proj.get("name", ""),
                    "slug": slug,
                    "status": proj.get("status", "design"),
                    "effect_type": proj.get("effect_type"),
                    "description": proj.get("description"),
                    "notes": proj.get("notes"),
                    "schematic_id": proj.get("schematic_id"),
                    "created_at": ts,
                    "updated_at": ts,
                })
                for row in proj.get("bom", []):
                    bid += 1
                    bom_items.append({
                        "id": bid,
                        "project_id": pid,
                        "category": row.get("category", ""),
                        "value": row.get("value", ""),
                        "quantity": int(row.get("quantity", 1) or 1),
                        "component_id": row.get("component_id"),
                        "reference": row.get("reference"),
                        "notes": row.get("notes"),
                        "is_optional": int(row.get("is_optional", 0) or 0),
                        "created_at": ts,
                    })
            self._write_raw("projects", projects)
            self._write_raw("bom_items", bom_items)

        # --- empty collections ---
        if not self._path("supplier_listings").exists():
            self._write_raw("supplier_listings", [])
        if not self._path("schematics").exists():
            self._write_raw("schematics", [])
        if not self._path("settings").exists():
            self._write_raw("settings", {})

    # --------------------------------------------------------------- id alloc
    @staticmethod
    def _next_id(rows: List[Dict[str, Any]]) -> int:
        return (max((int(r.get("id", 0)) for r in rows), default=0)) + 1

    # =====================================================================
    # Components
    # =====================================================================
    def list_components(self) -> List[Component]:
        return [Component.from_dict(d) for d in self._read_raw("components", [])]

    def get_component(self, cid: int) -> Optional[Component]:
        for d in self._read_raw("components", []):
            if int(d.get("id")) == cid:
                return Component.from_dict(d)
        return None

    def add_component(self, comp: Component) -> Component:
        rows = self._read_raw("components", [])
        comp.id = self._next_id(rows)
        ts = _now_iso()
        comp.created_at = comp.created_at or ts
        comp.updated_at = ts
        rows.append(comp.to_dict())
        self._write_raw("components", rows)
        return comp

    def update_component(self, comp: Component) -> None:
        rows = self._read_raw("components", [])
        comp.updated_at = _now_iso()
        for i, d in enumerate(rows):
            if int(d.get("id")) == comp.id:
                rows[i] = comp.to_dict()
                break
        self._write_raw("components", rows)

    def delete_component(self, cid: int) -> None:
        rows = [d for d in self._read_raw("components", []) if int(d.get("id")) != cid]
        self._write_raw("components", rows)

    def adjust_quantity(self, cid: int, delta: int) -> Optional[Component]:
        """Adjust inventory quantity by delta. Clamps to 0 (never negative)."""
        rows = self._read_raw("components", [])
        updated: Optional[Component] = None
        for i, d in enumerate(rows):
            if int(d.get("id")) == cid:
                d["quantity"] = max(0, int(d.get("quantity", 0)) + delta)
                d["updated_at"] = _now_iso()
                rows[i] = d
                updated = Component.from_dict(d)
                break
        if updated is not None:
            self._write_raw("components", rows)
        return updated

    def component_categories(self) -> List[str]:
        cats = sorted({c.category for c in self.list_components() if c.category})
        return cats

    # =====================================================================
    # Projects
    # =====================================================================
    def list_projects(self) -> List[Project]:
        return [Project.from_dict(d) for d in self._read_raw("projects", [])]

    def get_project(self, pid: int) -> Optional[Project]:
        for d in self._read_raw("projects", []):
            if int(d.get("id")) == pid:
                return Project.from_dict(d)
        return None

    def add_project(self, proj: Project) -> Project:
        rows = self._read_raw("projects", [])
        proj.id = self._next_id(rows)
        if not proj.slug:
            proj.slug = self._slugify(proj.name)
        ts = _now_iso()
        proj.created_at = proj.created_at or ts
        proj.updated_at = ts
        rows.append(proj.to_dict())
        self._write_raw("projects", rows)
        return proj

    def update_project(self, proj: Project) -> None:
        rows = self._read_raw("projects", [])
        proj.updated_at = _now_iso()
        for i, d in enumerate(rows):
            if int(d.get("id")) == proj.id:
                rows[i] = proj.to_dict()
                break
        self._write_raw("projects", rows)

    def delete_project(self, pid: int) -> None:
        rows = [d for d in self._read_raw("projects", []) if int(d.get("id")) != pid]
        self._write_raw("projects", rows)
        # Cascade: remove that project's BOM items.
        bom = [d for d in self._read_raw("bom_items", []) if int(d.get("project_id")) != pid]
        self._write_raw("bom_items", bom)

    # =====================================================================
    # BOM items
    # =====================================================================
    def list_bom_items(self, project_id: Optional[int] = None) -> List[BOMItem]:
        rows = self._read_raw("bom_items", [])
        items = [BOMItem.from_dict(d) for d in rows]
        if project_id is not None:
            items = [b for b in items if b.project_id == project_id]
        return items

    def add_bom_item(self, item: BOMItem) -> BOMItem:
        rows = self._read_raw("bom_items", [])
        item.id = self._next_id(rows)
        item.created_at = item.created_at or _now_iso()
        rows.append(item.to_dict())
        self._write_raw("bom_items", rows)
        return item

    def update_bom_item(self, item: BOMItem) -> None:
        rows = self._read_raw("bom_items", [])
        for i, d in enumerate(rows):
            if int(d.get("id")) == item.id:
                rows[i] = item.to_dict()
                break
        self._write_raw("bom_items", rows)

    def delete_bom_item(self, bid: int) -> None:
        rows = [d for d in self._read_raw("bom_items", []) if int(d.get("id")) != bid]
        self._write_raw("bom_items", rows)

    # =====================================================================
    # Suppliers
    # =====================================================================
    def list_suppliers(self) -> List[Supplier]:
        return [Supplier.from_dict(d) for d in self._read_raw("suppliers", [])]

    def get_supplier(self, sid: int) -> Optional[Supplier]:
        for d in self._read_raw("suppliers", []):
            if int(d.get("id")) == sid:
                return Supplier.from_dict(d)
        return None

    # =====================================================================
    # Supplier listings
    # =====================================================================
    def list_supplier_listings(self) -> List[SupplierListing]:
        return [SupplierListing.from_dict(d) for d in self._read_raw("supplier_listings", [])]

    # =====================================================================
    # Schematics
    # =====================================================================
    def list_schematics(self) -> List[Schematic]:
        return [Schematic.from_dict(d) for d in self._read_raw("schematics", [])]

    def replace_schematics(self, schematics: List[Schematic]) -> None:
        self._write_raw("schematics", [s.to_dict() for s in schematics])

    def index_schematics_folder(self, folder: str) -> List[Schematic]:
        """Index image/PDF files under `folder` into the schematics collection.

        Recognised extensions: .gif .png .jpg .jpeg .pdf. The immediate parent
        directory name is used as the category_folder. Replaces the existing
        schematics collection.
        """
        exts = {".gif", ".png", ".jpg", ".jpeg", ".pdf"}
        root = Path(folder)
        found: List[Schematic] = []
        sid = 0
        if root.exists():
            for p in sorted(root.rglob("*")):
                if p.is_file() and p.suffix.lower() in exts:
                    sid += 1
                    try:
                        size: Optional[int] = p.stat().st_size
                    except Exception:
                        size = None
                    found.append(Schematic(
                        id=sid,
                        category_folder=p.parent.name,
                        file_name=p.name,
                        file_path=str(p),
                        file_type=p.suffix.lower().lstrip("."),
                        file_size=size,
                        effect_type=None,
                        tags=None,
                        created_at=_now_iso(),
                    ))
        self.replace_schematics(found)
        return found

    # =====================================================================
    # Settings
    # =====================================================================
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self._read_raw("settings", {}).get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        settings = self._read_raw("settings", {})
        settings[key] = value
        self._write_raw("settings", settings)

    # ---- Mouser API key (secure) ----
    def get_mouser_key(self) -> Optional[str]:
        if _HAS_KEYRING:
            try:
                val = keyring.get_password(_KEYRING_SERVICE, _MOUSER_KEY_NAME)
                if val:
                    return val
            except Exception:
                pass
        # Fallback: settings.json (plaintext -- see module docstring tradeoff).
        return self.get_setting(_MOUSER_KEY_NAME) or None

    def set_mouser_key(self, key: str) -> None:
        key = (key or "").strip()
        if _HAS_KEYRING:
            try:
                if key:
                    keyring.set_password(_KEYRING_SERVICE, _MOUSER_KEY_NAME, key)
                else:
                    try:
                        keyring.delete_password(_KEYRING_SERVICE, _MOUSER_KEY_NAME)
                    except Exception:
                        pass
                # Make sure no stale plaintext copy lingers.
                if self.get_setting(_MOUSER_KEY_NAME):
                    self.set_setting(_MOUSER_KEY_NAME, "")
                return
            except Exception:
                pass
        # Fallback path.
        self.set_setting(_MOUSER_KEY_NAME, key)

    def key_storage_backend(self) -> str:
        """Human-readable description of where the Mouser key is stored."""
        return "OS keyring" if _HAS_KEYRING else "settings.json (plaintext)"
