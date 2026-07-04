# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
Generate the NATIVE app's schematic index (schematics.json).

Scans the schematics repo (this repo's parent directory), classifies each file
(effect_type via CATEGORY_MAP + filename tags), and writes the index with
ABSOLUTE file paths to:
  1. native/Sources/WorkshopCore/Resources/schematics.json  (bundle seed)
  2. ~/Library/Application Support/PedalWorkshop/schematics.json  (live copy)

This replaces scripts/index_schematics.py for the native app (that script
writes to the deprecated web-stack SQLite DB, not the JSON the app reads).

Deterministic: sorted by (category, filename); ids are stable for a given
tree state. Run again after adding/renaming schematic files. Usage:
  python3 scripts/generate_native_index.py [--dry-run]
"""
import json
import sys
from datetime import datetime
from pathlib import Path

WORKSHOP = Path(__file__).resolve().parent.parent
ROOT = WORKSHOP.parent  # the schematics repo
BUNDLE_JSON = WORKSHOP / "native/Sources/WorkshopCore/Resources/schematics.json"
APPSUPPORT_JSON = Path.home() / "Library/Application Support/PedalWorkshop/schematics.json"

SKIP_DIRS = {"workshop", "picocalc-bench"}
VALID_EXT = {".gif", ".pdf", ".png", ".jpg", ".jpeg"}

CATEGORY_MAP = {
    "ADSR Generators and Envelope Generators": "envelope",
    "Amplifiers and VCAs": "amplifier",
    "Buffers Switchers Mixers and Routers": "utility",
    "Chorus": "chorus",
    "Circuit Bending and Modifications": "modification",
    "Compressors Gates and Limiters": "compressor",
    "Delay Echo and Samplers": "delay",
    "Distortion Boost and Overdrive": "distortion",
    "Filters Wahs and VCFs": "filter",
    "Flangers": "flanger",
    "Full Synths Drum Synths and Misc Synth": "synth",
    "Fuzz and Fuzzy Noisemakers": "fuzz",
    "Guitar Synth and Misc Signal Shapers": "synth",
    "MIDI": "midi",
    "Miscellaneous": "misc",
    "OOP Japanese Electronics Book": "reference",
    "Oscillators LFOs and Signal Generators": "oscillator",
    "Phasers": "phaser",
    "Power Supplies and Other Useful Stuff": "power",
    "Reverb": "reverb",
    "Ring Modulators and Frequency Shifters": "ring_mod",
    "Tone Control and EQs": "eq",
    "Tremolos and Panners": "tremolo",
    "Vibrato and Pitch Shift": "pitch",
}


def build_index() -> list[dict]:
    entries = []
    for cat_dir in sorted(ROOT.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name in SKIP_DIRS or cat_dir.name.startswith("."):
            continue
        effect_type = CATEGORY_MAP.get(cat_dir.name)
        for f in sorted(cat_dir.iterdir()):
            if not f.is_file() or f.suffix.lower() not in VALID_EXT:
                continue
            stat = f.stat()
            if stat.st_size <= 512:  # scrape-junk guard (Mod_Security stubs are 226 B)
                print(f"  SKIP junk-sized ({stat.st_size} B): {f}", file=sys.stderr)
                continue
            tags = [t.lower() for t in f.stem.replace("-", " ").replace("_", " ").split() if len(t) > 1]
            if effect_type:
                tags.append(effect_type)
            entries.append({
                "category_folder": cat_dir.name,
                "file_name": f.name,
                "file_path": str(f),
                "file_type": f.suffix.lower().lstrip("."),
                "file_size": stat.st_size,
                "effect_type": effect_type,
                "tags": sorted(set(tags)),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            })
    for i, e in enumerate(entries, 1):
        e["id"] = i
    return entries


def main() -> None:
    dry = "--dry-run" in sys.argv
    entries = build_index()
    typed = sum(1 for e in entries if e["effect_type"])
    print(f"indexed {len(entries)} schematics ({typed} with effect_type, "
          f"{len({e['category_folder'] for e in entries})} categories)")
    if dry:
        return
    payload = json.dumps(entries, indent=1, ensure_ascii=False)
    BUNDLE_JSON.write_text(payload)
    print(f"wrote {BUNDLE_JSON}")
    if APPSUPPORT_JSON.parent.is_dir():
        APPSUPPORT_JSON.write_text(payload)
        print(f"wrote {APPSUPPORT_JSON}")


if __name__ == "__main__":
    main()
