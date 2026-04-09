#!/usr/bin/env python3
"""Index the existing schematic library into the database."""

import sys
from pathlib import Path

# Add workshop root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.config import settings
from api.database import SessionLocal, engine
from api.models.base import Base
from api.models.schematic import Schematic  # noqa: F401
from api.services.schematic_indexer import index_schematics


def main():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        count = index_schematics(db, settings.schematics_root)
        total = db.query(Schematic).count()
        print(f"Indexed {count} new schematics ({total} total in database)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
