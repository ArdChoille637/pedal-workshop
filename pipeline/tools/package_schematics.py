#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
package_schematics.py — copy the indexed schematic files INTO the app bundle.

The macOS app reads schematic images/PDFs only from its own bundle, never from
~/Documents (which triggers the Documents-folder permission prompt and can hang
the app). This script copies each indexed file into

    native/Sources/WorkshopCore/Resources/Schematics/<category_folder>/<file_name>

which Package.swift bundles via `.copy("Resources/Schematics")`. The files are
gitignored (copyrighted + large); a fresh clone ships an empty library.

Run after changing your schematic library, then rebuild the app:

    python3 pipeline/tools/package_schematics.py
    cd native && ./launch.sh

Index source (default): ~/Library/Application Support/PedalWorkshop/schematics.json
Override with:          package_schematics.py /path/to/schematics.json
"""
import json
import os
import shutil
import sys
from pathlib import Path

# repo root = three levels up from pipeline/tools/this-file
REPO = Path(__file__).resolve().parents[2]
DEST_ROOT = REPO / "native/Sources/WorkshopCore/Resources/Schematics"
DEFAULT_INDEX = Path.home() / "Library/Application Support/PedalWorkshop/schematics.json"


def main() -> int:
    index_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INDEX
    if not index_path.exists():
        print(f"error: index not found: {index_path}", file=sys.stderr)
        print("Generate it first with pipeline/tools/generate_native_index.py, "
              "or pass an index path.", file=sys.stderr)
        return 1

    entries = json.loads(index_path.read_text())
    DEST_ROOT.mkdir(parents=True, exist_ok=True)

    copied = skipped = missing = 0
    total_bytes = 0
    for e in entries:
        src = Path(e.get("file_path", ""))
        category = e.get("category_folder", "")
        name = e.get("file_name", "")
        if not src or not category or not name:
            continue
        if not src.exists():
            missing += 1
            continue
        dest = DEST_ROOT / category / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Idempotent: skip if an identical-size copy is already bundled.
        if dest.exists() and dest.stat().st_size == src.stat().st_size:
            skipped += 1
            total_bytes += dest.stat().st_size
            continue
        shutil.copy2(src, dest)
        copied += 1
        total_bytes += dest.stat().st_size

    print(f"packaged {copied + skipped} schematic files into {DEST_ROOT}")
    print(f"  copied {copied}, unchanged {skipped}, missing-source {missing}")
    print(f"  bundle library size: {total_bytes / 1e6:.1f} MB")
    if missing:
        print(f"  ({missing} indexed files were not found on disk and skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
