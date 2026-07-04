# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
# https://github.com/ArdChoille637/pedal-workshop

#!/usr/bin/env python3
"""
Analyze all 881 schematics via OCR and extract BOM data.
Writes schematics_metadata.json to Application Support.

For each schematic extracts:
  - component references (R1, C3, Q2, IC1, D1, SW1...)
  - resistor values  (10k, 4.7k, 1M, 470R, 4K7 European...)
  - capacitor values (100nF, 47uF, 220pF, 4n7 European...)
  - IC / chip names  (TL072, LM386, PT2399, XR2206, MAX1044...)
  - diodes, transistors, pots, switches
  - supply voltages  (+9V, +12V, ±15V...)
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
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
APP_SUPPORT     = Path.home() / "Library" / "Application Support" / "PedalWorkshop"
SCHEMATICS_JSON = APP_SUPPORT / "schematics.json"
OUTPUT_JSON     = APP_SUPPORT / "schematics_metadata.json"
WORK_DIR        = Path(tempfile.gettempdir()) / "pedal_ocr"
WORK_DIR.mkdir(exist_ok=True)

# ── Component value patterns ──────────────────────────────────────────────────

# Standard notation: 10k, 4.7K, 100k, 1M, 470R, 470 ohm
RE_RESISTOR = re.compile(
    r'\b(\d+(?:[.,]\d+)?)\s*'
    r'(meg|M(?:ohm)?|[kK](?:ohm)?|[Rr](?:ohm)?|ohm|Ω)s?\b',
    re.IGNORECASE
)

# European/EIA notation: 4K7 = 4.7k, 1M5 = 1.5M, 2R2 = 2.2 ohm, 100R = 100 ohm
RE_R_EURO = re.compile(r'\b(\d+)([KkMmRr])(\d)\b')

# Assignment style: "R1 = 10k" or "R1: 10k"
RE_R_ASSIGN = re.compile(
    r'\b[Rr]\d+\w*\s*[=:]\s*(\d+(?:[.,]\d+)?)\s*(meg|M|k|K|R|ohm)?\b',
    re.IGNORECASE
)

# Capacitors — standard: 100n, 47u, 220p, 10uF, .047uF, 0.1uF
RE_CAP = re.compile(
    r'\b(\d+(?:[.,]\d+)?|[.,]\d+)\s*'
    r'(µ[Ff]?|uF?|nF?|pF?|µ|u|n|p)\b',
    re.IGNORECASE
)

# European/EIA capacitor notation: 4n7 = 4.7nF, 47u = 47uF, 100p5 = 100.5pF (rare)
RE_C_EURO = re.compile(r'\b(\d+)([NnUuPp])(\d)\b')

# ICs / chips — extended to cover common pedal and synth chips
RE_IC = re.compile(
    r'\b('
    # Op-amps / audio
    r'TL\d{3,4}[A-Z]*|'
    r'LM\d{3,4}[A-Z]*|'
    r'LF\d{3,4}[A-Z]*|'
    r'NE\d{4}[A-Z]*|'
    r'SE\d{4}[A-Z]*|'
    r'MC\d{4}[A-Z]*|'
    r'CA\d{4}[A-Z]*|'
    r'RC\d{4}[A-Z]*|'
    r'OP\d{3}[A-Z]*|'
    r'UA\d{3}[A-Z]*|'
    r'μA\d{3}[A-Z]*|'
    r'JRC\d{4}[A-Z]*|'
    r'NJM\d{4}[A-Z]*|'
    # Delay / BBD chips
    r'PT\d{4}[A-Z]*|'
    r'MN\d{4}[A-Z]*|'
    r'SAD\d{4}[A-Z]*|'
    r'TDA\d{4}[A-Z]*|'
    # VCAs / OTAs / filters
    r'SSM\d{4}[A-Z]*|'
    r'CEM\d{4}[A-Z]*|'
    r'AS\d{4}[A-Z]*|'
    r'V\d{4}[A-Z]*|'
    r'BA\d{4}[A-Z]*|'
    r'AN\d{4}[A-Z]*|'
    # Function generators / oscillators
    r'XR\d{4}[A-Z]*|'
    r'ICL\d{4}[A-Z]*|'
    r'MAX\d{4}[A-Z]*|'
    r'LT\d{4}[A-Z]*|'
    # Logic / CMOS
    r'CD\d{4}[A-Z]*|'
    r'HCF\d{4}[A-Z]*|'
    r'HEF\d{4}[A-Z]*|'
    r'SN\d{5}[A-Z]*|'
    # Misc / regulators
    r'IR\d{4}[A-Z]*|'
    r'HF\d{4}[A-Z]*|'
    # Bare common part numbers: 741, 741C, 386, 4049, 4069, 4558
    r'(?<!\d)741[A-Z]?(?!\d)|'
    r'4558[A-Z]?|'
    r'386[A-Z]?(?!\d)'
    r')\b'
)

# Transistors: 2N3904, 2N5088, BC108, BC547, MPSA18, J201, MPF102
RE_TRANSISTOR = re.compile(
    r'\b('
    r'2N\d{3,4}[A-Z]*|'
    r'BC\d{2,3}[A-Z]*|'
    r'BD\d{2,3}[A-Z]*|'
    r'BF\d{2,3}[A-Z]*|'
    r'BS\d{2,3}[A-Z]*|'
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

# Potentiometers: A500K, B100K, C10K, 500k audio, 100k log, 50k lin
RE_POT = re.compile(
    r'\b([AB]?\s*\d+(?:[.,]\d+)?\s*[KkMm])\s*(?:log|lin|audio|linear|reverse|rev|A|B|C)\b|'
    r'\bpot(?:entiometer)?\s*[=:]?\s*([AB]?\d+[KkMm])\b',
    re.IGNORECASE
)

# Supply voltages: +9V, -12V, ±15V, 9VDC, 5V rail
RE_VOLTAGE = re.compile(
    r'([+\-±]?\s*\d+(?:\.\d+)?)\s*[Vv](?:\s*(?:DC|AC|supply|rail|bias|reg))?\b'
)

# Component reference designators
RE_REFS = re.compile(r'\b([RCDQULBFJTPSVMK]\d{1,3}[A-Z]?)\b')

# Known part name mentions (case-insensitive substring scan)
KNOWN_PARTS = {
    "3PDT":      ("switch",          "3PDT"),
    "DPDT":      ("switch",          "DPDT"),
    "SPDT":      ("switch",          "SPDT"),
    "3pdt":      ("switch",          "3PDT"),
    "stomp":     ("switch",          "3PDT"),
    "LDR":       ("other",           "LDR"),
    "LED":       ("diode",           "LED 3mm Red"),
    "trimpot":   ("potentiometer",   "10k linear"),
    "trimmer":   ("potentiometer",   "10k linear"),
    "trim pot":  ("potentiometer",   "10k linear"),
    "vactrol":   ("other",           "Vactrol"),
    "opto":      ("other",           "Optocoupler"),
    "transformer": ("other",         "Transformer"),
    "relay":     ("other",           "Relay"),
    "crystal":   ("other",           "Crystal"),
    "resonator": ("other",           "Resonator"),
    "ferrite":   ("other",           "Ferrite Bead"),
    "power jack": ("jack",           "2.1mm DC Jack"),
    "dc jack":   ("jack",            "2.1mm DC Jack"),
    "input jack": ("jack",           "1/4\" Mono Jack"),
    "output jack": ("jack",          "1/4\" Mono Jack"),
    "1/4":       ("jack",            "1/4\" Mono Jack"),
    "charge pump": ("ic",            "MAX1044"),
    "7805":      ("ic",              "7805"),
    "7809":      ("ic",              "7809"),
    "7812":      ("ic",              "7812"),
    "78L05":     ("ic",              "78L05"),
    "78L09":     ("ic",              "78L09"),
    "LT1054":    ("ic",              "LT1054"),
    "MAX1044":   ("ic",              "MAX1044"),
    "ICL7660":   ("ic",              "ICL7660"),
}

# Common OCR character substitutions in part numbers.
# Each entry is (compiled_pattern, replacement_string).
# Only add rules that cannot fire on valid electronics text.
OCR_CORRECTIONS = [
    # "B" misread as "8" in transistor prefix: "8C547" → "BC547", "8D139" → "BD139"
    (re.compile(r'\b8([CDFSN]\d{2,3})\b'), r'B\1'),
    # Leading "I" misread instead of "1" in diode numbers: "IN4148" → "1N4148"
    # Safe because no legitimate part starts with uppercase I followed by N+digits.
    (re.compile(r'\bIN(\d{2,4}[A-Z]*)\b'), r'1N\1'),
    # "B" misread as "8" in middle of LM386: "LM3B6" → "LM386"
    (re.compile(r'\bLM3B(\d)\b'), r'LM38\1'),
]


# ── Value normalization ────────────────────────────────────────────────────────

def normalize_r(val: str, unit: str) -> str:
    """Normalize resistor → canonical string like '10k', '4.7k', '1M', '470'."""
    val = val.replace(",", ".")
    u = unit.lower().strip()
    if u in ("k", "kohm"):
        return f"{val}k"
    if u in ("m", "meg", "mohm"):
        return f"{val}M"
    if u in ("r", "ohm", "ω", ""):
        # Strip trailing .0
        try:
            n = float(val)
            return str(int(n)) if n == int(n) else val
        except ValueError:
            return val
    return f"{val}{unit}"


def normalize_r_euro(before: str, sep: str, after: str) -> str:
    """Normalize European resistor notation: 4K7 → 4.7k, 2M2 → 2.2M, 2R2 → 2.2."""
    s = sep.upper()
    val = f"{before}.{after}"
    if s == "K":
        return f"{val}k"
    if s == "M":
        return f"{val}M"
    return val  # R = ohm


def normalize_cap(val: str, unit: str) -> str:
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


def normalize_cap_euro(before: str, sep: str, after: str) -> str:
    """Normalize European cap notation: 4n7 → 4.7nF, 47u5 → 47.5uF."""
    s = sep.upper()
    val = f"{before}.{after}"
    if s == "N":
        return f"{val}nF"
    if s == "U":
        return f"{val}uF"
    if s == "P":
        return f"{val}pF"
    return f"{val}{sep}"


def correct_ocr(text: str) -> str:
    """Fix common OCR substitution errors in electronics part numbers."""
    for pattern, replacement in OCR_CORRECTIONS:
        text = pattern.sub(replacement, text)
    return text


# ── BOM extraction ────────────────────────────────────────────────────────────

def build_bom_entries(text: str) -> list[dict]:
    """
    Parse OCR text and return a list of BOM-like dicts:
      {"category", "value", "quantity": N, "source": "ocr"}

    Quantities reflect how many times each distinct value appeared in the text
    (useful for counting 10k resistors, 100nF caps, etc.).
    """
    text = correct_ocr(text)
    counts: dict[tuple[str, str], int] = defaultdict(int)

    # Resistors — standard notation
    for m in RE_RESISTOR.finditer(text):
        v = normalize_r(m.group(1), m.group(2))
        if v:
            counts[("resistor", v)] += 1

    # Resistors — European notation (4K7, 2M2, 2R2)
    for m in RE_R_EURO.finditer(text):
        v = normalize_r_euro(m.group(1), m.group(2), m.group(3))
        if v:
            counts[("resistor", v)] += 1

    # Capacitors — standard notation
    for m in RE_CAP.finditer(text):
        v = normalize_cap(m.group(1), m.group(2))
        if v:
            counts[("capacitor", v)] += 1

    # Capacitors — European notation (4n7, 47u5)
    for m in RE_C_EURO.finditer(text):
        v = normalize_cap_euro(m.group(1), m.group(2), m.group(3))
        if v:
            counts[("capacitor", v)] += 1

    # ICs
    for m in RE_IC.finditer(text):
        v = m.group(1).upper()
        counts[("ic", v)] += 1

    # Transistors
    for m in RE_TRANSISTOR.finditer(text):
        v = m.group(1)
        if v in ("PNP", "NPN"):
            counts[("transistor", f"{v} generic")] += 1
        else:
            counts[("transistor", v.upper())] += 1

    # Diodes
    for m in RE_DIODE.finditer(text):
        v = m.group(1)
        vl = v.lower()
        if "germanium" in vl or vl.strip() == "ge":
            counts[("diode", "1N34A")] += 1
        elif "schottky" in vl:
            counts[("diode", "1N5817")] += 1
        elif "silicon" in vl:
            counts[("diode", "1N4148")] += 1
        else:
            counts[("diode", v.upper())] += 1

    # Potentiometers
    for m in RE_POT.finditer(text):
        v = (m.group(1) or m.group(2) or "").strip().replace(" ", "")
        if v:
            counts[("potentiometer", v.upper())] += 1

    # Known named parts (counted once each — they appear as keywords not values)
    text_lower = text.lower()
    for keyword, (cat, val) in KNOWN_PARTS.items():
        if keyword.lower() in text_lower:
            if (cat, val) not in counts:
                counts[(cat, val)] = 1

    return [
        {"category": cat, "value": val, "quantity": qty, "source": "ocr"}
        for (cat, val), qty in counts.items()
        if val
    ]


def extract_voltages(text: str) -> list[str]:
    """Extract supply voltage mentions from OCR text."""
    found = []
    seen = set()
    for m in RE_VOLTAGE.finditer(text):
        v = m.group(0).strip()
        norm = v.replace(" ", "")
        if norm not in seen:
            seen.add(norm)
            found.append(norm)
    return found[:8]  # cap at 8 to avoid noise


# ── Image preprocessing ───────────────────────────────────────────────────────

def preprocess_image(img_path: Path, sid: int) -> Path:
    """
    Enhance a schematic image for better Tesseract accuracy on poor-quality scans.

    Pipeline:
      1. Convert to grayscale
      2. Upscale to at least 2000px on longest axis (important for small/low-res images)
      3. Enhance contrast (CLAHE-style via Pillow)
      4. Unsharp mask to sharpen edges
      5. Save as PNG (lossless, avoids JPEG re-compression artifacts)

    Falls back to the original path if Pillow is not installed.
    """
    try:
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    except ImportError:
        return img_path

    try:
        img = Image.open(img_path)

        # Handle multi-frame GIFs — seek to first frame
        if hasattr(img, "n_frames") and img.n_frames > 1:
            img.seek(0)
        img = img.copy()  # detach from file handle after seek

        # Convert to grayscale
        if img.mode not in ("L", "LA"):
            img = img.convert("L")

        # Upscale if the image is too small for reliable OCR
        # Rule of thumb: characters need to be ~30px tall; most schematics
        # have text ~10pt which at 72 DPI = 10px → need 3x scale minimum
        w, h = img.size
        min_dim = min(w, h)
        if min_dim < 1200:
            scale = max(1200 / min_dim, 1.5)
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        # Enhance contrast — helps with faded photocopies
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = ImageEnhance.Sharpness(img).enhance(2.0)

        # Unsharp mask — crisp edges matter for OCR
        img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=2))

        out_path = WORK_DIR / f"s{sid}_prep.png"
        img.save(str(out_path), "PNG")
        return out_path

    except Exception:
        return img_path


# ── OCR ───────────────────────────────────────────────────────────────────────

_PSM_MODES = (11, 6, 3)  # sparse text, uniform block, auto — tried in order


def run_tesseract(img_path: Path, sid: int) -> str:
    """
    Run Tesseract with multiple PSM modes and return the result with the most
    recognized words.  Uses LSTM engine (--oem 3) for best accuracy.
    """
    best_text = ""
    best_score = -1

    for psm in _PSM_MODES:
        out_stem = WORK_DIR / f"s{sid}_psm{psm}"
        try:
            subprocess.run(
                [
                    "tesseract", str(img_path), str(out_stem),
                    "--psm", str(psm),
                    "--oem", "3",
                    "-l", "eng",
                    "-c", "tessedit_char_whitelist="
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                    "0123456789+-.,/=:;μΩ±°() ",
                ],
                capture_output=True,
                timeout=90,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

        txt_file = Path(str(out_stem) + ".txt")
        if not txt_file.exists():
            continue

        text = txt_file.read_text(errors="replace")
        # Score = word count, weighted toward results that contain electronics tokens
        words = len(text.split())
        elec_tokens = len(RE_IC.findall(text)) + len(RE_TRANSISTOR.findall(text)) + \
                      len(RE_RESISTOR.findall(text)) + len(RE_CAP.findall(text))
        score = words + elec_tokens * 5

        if score > best_score:
            best_score = score
            best_text = text

        # If we already found rich electronics text, no need to try other modes
        if elec_tokens >= 3:
            break

    return best_text


def ocr_schematic(schematic: dict) -> dict:
    """OCR one schematic file and extract BOM data. Returns enriched dict."""
    path = Path(schematic["file_path"])
    ext  = schematic["file_type"].lower()
    sid  = schematic["id"]

    img_path: Path | None = None

    try:
        if ext == "pdf":
            # Render at 300 DPI for crisp text on old/photocopied schematics
            out_stem = str(WORK_DIR / f"s{sid}")
            subprocess.run(
                ["pdftoppm", "-r", "300", "-png", "-f", "1", "-l", "1",
                 str(path), out_stem],
                capture_output=True,
                timeout=60,
            )
            candidate = WORK_DIR / f"s{sid}-1.png"
            if candidate.exists():
                img_path = candidate

        elif ext in ("gif", "jpg", "jpeg", "png"):
            img_path = path

        if img_path is None or not img_path.exists():
            return _result(schematic, "", [], [])

        # Preprocess for better OCR (upscale, contrast, sharpen)
        img_path = preprocess_image(img_path, sid)

        text    = run_tesseract(img_path, sid)
        bom     = build_bom_entries(text)
        refs    = sorted(set(RE_REFS.findall(text)))
        volts   = extract_voltages(text)

    except subprocess.TimeoutExpired:
        return _result(schematic, "", [], [])
    except Exception:
        return _result(schematic, "", [], [])

    return _result(schematic, text[:1500], bom, refs, volts)


def _result(schematic: dict, text_excerpt: str, bom: list, refs: list,
            voltages: list | None = None) -> dict:
    return {
        "id":              schematic["id"],
        "file_name":       schematic["file_name"],
        "category_folder": schematic["category_folder"],
        "file_type":       schematic["file_type"],
        "file_path":       schematic["file_path"],
        "text_excerpt":    text_excerpt.strip()[:800],
        "refs_found":      refs,
        "ref_count":       len(refs),
        "bom_entries":     bom,
        "bom_count":       len(bom),
        "supply_voltages": voltages or [],
        "analyzed":        True,
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
    existing: dict[int, dict] = {}
    if OUTPUT_JSON.exists() and not args.force:
        with open(OUTPUT_JSON) as f:
            for item in json.load(f):
                existing[item["id"]] = item
        print(f"Resuming — {len(existing)} already analyzed, "
              f"{len(schematics) - len(existing)} remaining")

    todo  = [s for s in schematics if s["id"] not in existing]
    print(f"Analyzing {len(todo)} schematics with {args.workers} workers…\n")

    results = dict(existing)
    done    = len(existing)
    total   = len(schematics)
    start   = time.time()
    errors  = 0

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(ocr_schematic, s): s for s in todo}
        for future in as_completed(futures):
            try:
                r = future.result()
                results[r["id"]] = r
                done += 1
                bom_n = r["bom_count"]
                ref_n = r.get("ref_count", 0)
                marker = "✓" if bom_n > 0 else "·"
                if done <= 30 or done % 50 == 0 or bom_n > 5:
                    elapsed = time.time() - start
                    rate    = (done - len(existing)) / max(elapsed, 1)
                    eta     = (total - done) / max(rate, 0.01)
                    volts   = ",".join(r.get("supply_voltages", [])[:2])
                    print(
                        f"  [{done:>4}/{total}] {marker} "
                        f"{bom_n:>2}bom {ref_n:>3}refs "
                        f"{('  '+volts)[:8]}  "
                        f"{r['file_name'][:45]:<45}  "
                        f"ETA {eta:.0f}s"
                    )
            except Exception as e:
                errors += 1
                print(f"  ERROR: {e}")

            # Checkpoint every 100
            if done % 100 == 0:
                _write(results, OUTPUT_JSON)

    _write(results, OUTPUT_JSON)
    elapsed = time.time() - start

    # Stats
    all_results  = list(results.values())
    with_bom     = [r for r in all_results if r["bom_count"] > 0]
    with_refs    = [r for r in all_results if r.get("ref_count", 0) > 0]
    with_volts   = [r for r in all_results if r.get("supply_voltages")]
    total_parts  = sum(r["bom_count"] for r in all_results)
    print(f"\n{'─'*65}")
    print(f"Analyzed:         {len(all_results)}")
    print(f"With BOM data:    {len(with_bom):>4}  ({100*len(with_bom)//max(len(all_results),1)}%)")
    print(f"With refs:        {len(with_refs):>4}  ({100*len(with_refs)//max(len(all_results),1)}%)")
    print(f"With voltages:    {len(with_volts):>4}  ({100*len(with_volts)//max(len(all_results),1)}%)")
    print(f"Total BOM parts:  {total_parts}")
    print(f"Errors:           {errors}")
    print(f"Time:             {elapsed:.0f}s")
    print(f"Output:           {OUTPUT_JSON}")


def _write(results: dict, path: Path) -> None:
    out = sorted(results.values(), key=lambda x: x["id"])
    with open(path, "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
