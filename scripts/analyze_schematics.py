# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
# https://github.com/ArdChoille637/pedal-workshop

#!/usr/bin/env python3
"""
Analyze all 881 schematics via OCR and extract BOM data.
Writes schematics_metadata.json to Application Support.

For each schematic extracts:
  - component references (R1, C3, Q2, IC1, D1, SW1...)
  - resistor values  (10k, 4.7k, 1M, 470R...)
  - capacitor values (100nF, 47uF, 220pF...)
  - IC / chip names  (TL072, LM386, PT2399, 2N3904...)
  - diodes, transistors, pots, switches
  - inferred BOM list normalized to match inventory schema

Usage: python3 analyze_schematics.py [--workers N] [--force]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
APP_SUPPORT  = Path.home() / "Library" / "Application Support" / "PedalWorkshop"
SCHEMATICS_JSON = APP_SUPPORT / "schematics.json"
OUTPUT_JSON     = APP_SUPPORT / "schematics_metadata.json"
WORK_DIR        = Path(tempfile.gettempdir()) / "pedal_ocr"
WORK_DIR.mkdir(exist_ok=True)

# ── Component value patterns ──────────────────────────────────────────────────

# Resistors: 10k, 4.7K, 100k, 1M, 470R, 470, 1 meg
RE_RESISTOR = re.compile(
    r'\b(\d+(?:[.,]\d+)?)\s*'
    r'(meg|M(?:ohm)?|[kK](?:ohm)?|[Rr](?:ohm)?|ohm|Ω)s?\b',
    re.IGNORECASE
)
# Also catch bare numbers next to known R refs: "R1 = 10k"
RE_R_ASSIGN = re.compile(
    r'\b[Rr]\d+\w*\s*[=:]\s*(\d+(?:[.,]\d+)?)\s*(meg|M|k|K|R|ohm)?\b',
    re.IGNORECASE
)

# Capacitors: 100n, 47u, 220p, 10uF, .047uF, 0.1uF
RE_CAP = re.compile(
    r'\b(\d+(?:[.,]\d+)?|[.,]\d+)\s*'
    r'(µ[Ff]?|uF?|nF?|pF?|µ|u|n|p)\b',
    re.IGNORECASE
)

# ICs / chips: TL072, LM386, NE5532, PT2399, CD4049, MN3207, JRC4558, LM741
RE_IC = re.compile(
    r'\b('
    r'TL\d{3,4}[A-Z]*|'
    r'LM\d{3,4}[A-Z]*|'
    r'NE\d{4}[A-Z]*|'
    r'MC\d{4}[A-Z]*|'
    r'CA\d{4}[A-Z]*|'
    r'RC\d{4}[A-Z]*|'
    r'OP\d{3}[A-Z]*|'
    r'UA\d{3}[A-Z]*|'
    r'JRC\d{4}[A-Z]*|'
    r'PT\d{4}[A-Z]*|'
    r'MN\d{4}[A-Z]*|'
    r'V\d{4}[A-Z]*|'
    r'CD\d{4}[A-Z]*|'
    r'HF\d{4}[A-Z]*|'
    r'BA\d{4}[A-Z]*|'
    r'AN\d{4}[A-Z]*|'
    r'SSM\d{4}[A-Z]*|'
    r'CEM\d{4}[A-Z]*|'
    r'AS\d{4}[A-Z]*|'
    r'IR\d{4}[A-Z]*|'
    r'ICL\d{4}[A-Z]*'
    r')\b'
)

# Transistors: 2N3904, 2N5088, BC108, BC547, MPSA18, J201, MPF102
RE_TRANSISTOR = re.compile(
    r'\b('
    r'2N\d{3,4}[A-Z]*|'
    r'BC\d{2,3}[A-Z]*|'
    r'BD\d{2,3}[A-Z]*|'
    r'BF\d{2,3}[A-Z]*|'
    r'MPSA\d{2,3}[A-Z]*|'
    r'MPSU\d{2,3}[A-Z]*|'
    r'J\d{3}[A-Z]*|'
    r'MPF\d{3}[A-Z]*|'
    r'2SK\d{2,4}[A-Z]*|'
    r'2SJ\d{2,4}[A-Z]*|'
    r'PNP|NPN'
    r')\b'
)

# Diodes: 1N4148, 1N34A, BAT41, BAT46, 1N914
RE_DIODE = re.compile(
    r'\b('
    r'1N\d{2,4}[A-Z]*|'
    r'BAT\d{2}[A-Z]*|'
    r'BA\d{3}[A-Z]*|'
    r'1S\d{3}[A-Z]*|'
    r'GE\s*diode|germanium\s*diode|silicon\s*diode|schottky'
    r')\b',
    re.IGNORECASE
)

# Component reference designators
RE_REFS = re.compile(r'\b([RCDQULBFJTPSVMK]\d{1,3}[A-Z]?)\b')

# Known part name mentions (case-insensitive substring scan)
KNOWN_PARTS = {
    "3PDT": ("switch",    "3PDT"),
    "DPDT": ("switch",    "DPDT"),
    "SPDT": ("switch",    "SPDT"),
    "3pdt": ("switch",    "3PDT"),
    "stomp": ("switch",   "3PDT"),
    "LDR":  ("other",     "LDR"),
    "LED":  ("diode",     "LED 3mm Red"),
    "trimpot": ("potentiometer", "10k linear"),
    "trimmer":  ("potentiometer", "10k linear"),
    "vactrol":  ("other", "Vactrol"),
    "opto":     ("other", "Optocoupler"),
    "transformer": ("other", "Transformer"),
    "relay":    ("other", "Relay"),
    "crystal":  ("other", "Crystal"),
    "resonator": ("other", "Resonator"),
}

# ── Value normalization ────────────────────────────────────────────────────────

def normalize_r(val, unit):
    """Normalize resistor → canonical string like '10k', '4.7k', '1M', '470'."""
    val = val.replace(",", ".")
    u = unit.lower().strip()
    if u in ("k", "kohm"):
        return f"{val}k"
    if u in ("m", "meg", "mohm"):
        return f"{val}M"
    if u in ("r", "ohm", "ω", ""):
        return val
    return f"{val}{unit}"

def normalize_cap(val, unit):
    """Normalize cap → '100nF', '47uF', '220pF'."""
    val = val.replace(",", ".")
    if val.startswith("."):
        val = "0" + val
    u = unit.lower().replace("µ", "u").strip()
    if u in ("u", "uf"):
        return f"{val}uF"
    if u in ("n", "nf"):
        return f"{val}nF"
    if u in ("p", "pf"):
        return f"{val}pF"
    return f"{val}{unit}"

def build_bom_entries(text):
    """
    Parse OCR text and return a list of BOM-like dicts:
      {"category", "value", "quantity": 1, "source": "ocr"}
    """
    entries = []
    seen = set()

    def add(cat, val, qty=1):
        key = (cat, val.lower())
        if key not in seen and val:
            seen.add(key)
            entries.append({
                "category": cat,
                "value": val,
                "quantity": qty,
                "source": "ocr"
            })

    # Resistors
    for m in RE_RESISTOR.finditer(text):
        add("resistor", normalize_r(m.group(1), m.group(2)))

    # Capacitors
    for m in RE_CAP.finditer(text):
        add("capacitor", normalize_cap(m.group(1), m.group(2)))

    # ICs
    for m in RE_IC.finditer(text):
        add("ic", m.group(1).upper())

    # Transistors
    for m in RE_TRANSISTOR.finditer(text):
        v = m.group(1)
        if v in ("PNP", "NPN"):
            add("transistor", f"{v} generic")
        else:
            add("transistor", v.upper())

    # Diodes
    for m in RE_DIODE.finditer(text):
        v = m.group(1)
        vl = v.lower()
        if "germanium" in vl or "ge" == vl.strip():
            add("diode", "1N34A")
        elif "schottky" in vl:
            add("diode", "1N5817")
        elif "silicon" in vl:
            add("diode", "1N4148")
        elif v.upper() not in ("PNP", "NPN"):
            add("diode", v.upper())

    # Known named parts
    text_lower = text.lower()
    for keyword, (cat, val) in KNOWN_PARTS.items():
        if keyword.lower() in text_lower:
            add(cat, val)

    return entries

# ── OCR ───────────────────────────────────────────────────────────────────────

def ocr_schematic(schematic: dict) -> dict:
    """OCR one schematic file. Returns enriched dict."""
    path = Path(schematic["file_path"])
    ext  = schematic["file_type"].lower()
    sid  = schematic["id"]

    work_base = WORK_DIR / f"s{sid}"
    img_path  = None

    try:
        if ext == "pdf":
            out_stem = str(WORK_DIR / f"s{sid}")
            r = subprocess.run(
                ["pdftoppm", "-r", "150", "-png", "-f", "1", "-l", "1",
                 str(path), out_stem],
                capture_output=True, timeout=30
            )
            candidate = WORK_DIR / f"s{sid}-1.png"
            if candidate.exists():
                img_path = candidate
        elif ext in ("gif", "jpg", "jpeg", "png"):
            img_path = path

        if img_path is None or not img_path.exists():
            return _result(schematic, "", [])

        out_txt = WORK_DIR / f"s{sid}_out"
        r = subprocess.run(
            ["tesseract", str(img_path), str(out_txt),
             "--psm", "11",          # sparse text: good for schematics
             "-l", "eng"],
            capture_output=True, timeout=60
        )
        txt_file = Path(str(out_txt) + ".txt")
        text = txt_file.read_text(errors="replace") if txt_file.exists() else ""
        bom  = build_bom_entries(text)
        refs = list(set(RE_REFS.findall(text)))

    except subprocess.TimeoutExpired:
        return _result(schematic, "", [])
    except Exception:
        return _result(schematic, "", [])

    return _result(schematic, text[:1000], bom, refs)

def _result(schematic, text_excerpt, bom, refs=None):
    return {
        "id":             schematic["id"],
        "file_name":      schematic["file_name"],
        "category_folder": schematic["category_folder"],
        "file_type":      schematic["file_type"],
        "file_path":      schematic["file_path"],
        "text_excerpt":   text_excerpt.strip()[:500],
        "refs_found":     refs or [],
        "bom_entries":    bom,
        "bom_count":      len(bom),
        "analyzed":       True,
    }

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--force", action="store_true",
                        help="Re-analyze even if metadata already exists")
    args = parser.parse_args()

    with open(SCHEMATICS_JSON) as f:
        schematics = json.load(f)

    # Load existing results if resuming
    existing = {}
    if OUTPUT_JSON.exists() and not args.force:
        with open(OUTPUT_JSON) as f:
            for item in json.load(f):
                existing[item["id"]] = item
        print(f"Resuming — {len(existing)} already analyzed, "
              f"{len(schematics) - len(existing)} remaining")

    todo = [s for s in schematics if s["id"] not in existing]
    print(f"Analyzing {len(todo)} schematics with {args.workers} workers…\n")

    results = dict(existing)
    done = len(existing)
    total = len(schematics)
    start = time.time()
    errors = 0

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(ocr_schematic, s): s for s in todo}
        for future in as_completed(futures):
            try:
                r = future.result()
                results[r["id"]] = r
                done += 1
                bom_n = r["bom_count"]
                marker = "✓" if bom_n > 0 else "·"
                if done <= 30 or done % 50 == 0 or bom_n > 5:
                    elapsed = time.time() - start
                    rate = (done - len(existing)) / max(elapsed, 1)
                    eta  = (total - done) / max(rate, 0.01)
                    print(f"  [{done:>4}/{total}] {marker} "
                          f"{bom_n:>2} parts  "
                          f"{r['file_name'][:50]:<50}  "
                          f"ETA {eta:.0f}s")
            except Exception as e:
                errors += 1
                print(f"  ERROR: {e}")

            # Checkpoint every 100
            if done % 100 == 0:
                _write(results, OUTPUT_JSON)

    _write(results, OUTPUT_JSON)
    elapsed = time.time() - start

    # Stats
    all_results = list(results.values())
    with_bom  = [r for r in all_results if r["bom_count"] > 0]
    total_parts = sum(r["bom_count"] for r in all_results)
    print(f"\n{'─'*60}")
    print(f"Analyzed:      {len(all_results)}")
    print(f"With BOM data: {len(with_bom)}  ({100*len(with_bom)//len(all_results)}%)")
    print(f"Total parts extracted: {total_parts}")
    print(f"Errors:        {errors}")
    print(f"Time:          {elapsed:.0f}s")
    print(f"Output:        {OUTPUT_JSON}")

def _write(results, path):
    out = sorted(results.values(), key=lambda x: x["id"])
    with open(path, "w") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    main()
