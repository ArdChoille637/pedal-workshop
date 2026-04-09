# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
# https://github.com/ArdChoille637/pedal-workshop

#!/usr/bin/env python3
"""Seed the database with common components, suppliers, and a sample project."""

import json
import sys
from pathlib import Path

# Add workshop root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.database import SessionLocal
from api.models.base import Base
from api.models.component import Component
from api.models.project import BOMItem, Project
from api.models.supplier import Supplier
from api.database import engine

SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"


def seed():
    # Create tables if they don't exist (fallback if alembic hasn't run)
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        _seed_suppliers(db)
        _seed_components(db)
        _seed_sample_project(db)
        print("Seeding complete.")
    finally:
        db.close()


def _seed_suppliers(db):
    data = json.loads((SEEDS_DIR / "suppliers.json").read_text())
    existing = {s.slug for s in db.query(Supplier).all()}
    count = 0
    for entry in data:
        if entry["slug"] not in existing:
            db.add(Supplier(**entry))
            count += 1
    db.commit()
    print(f"  Suppliers: {count} added, {len(existing)} already existed")


def _seed_components(db):
    data = json.loads((SEEDS_DIR / "common_components.json").read_text())
    existing_count = db.query(Component).count()
    if existing_count > 0:
        print(f"  Components: skipped ({existing_count} already exist)")
        return
    for entry in data:
        db.add(Component(quantity=0, **entry))
    db.commit()
    print(f"  Components: {len(data)} added")


def _seed_sample_project(db):
    data = json.loads((SEEDS_DIR / "sample_project.json").read_text())
    existing = db.query(Project).filter_by(slug=data["slug"]).first()
    if existing:
        print(f"  Sample project: skipped ('{data['name']}' already exists)")
        return

    bom_data = data.pop("bom")
    project = Project(**data)
    db.add(project)
    db.flush()

    for item in bom_data:
        db.add(BOMItem(project_id=project.id, **item))

    db.commit()
    print(f"  Sample project: '{project.name}' with {len(bom_data)} BOM items")


if __name__ == "__main__":
    seed()
