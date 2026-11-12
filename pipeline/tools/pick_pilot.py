#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pick the 12-schematic pilot for the extraction-accuracy golden set.

Protocol: docs/fable-reply-v1.md §2.4 (pilot = 12, later folded into the 60-schematic
golden set). The pilot's job is to catch systematic failure modes cheaply, so the draw is
seeded + constrained rather than purely random:

  pool      has an extraction · slug is unique in the manifest (no slug collision) ·
            source file exists on disk · 10-80 parts (hand-readable in ~25 min) ·
            not utility/modification (mostly wiring diagrams) · not a no-parts file ·
            not `suspect-no-schematic` (the extractor itself said the image has no circuit)
  slots     one draw per slot: fuzz x2, distortion x2, filter, delay, eq, phaser,
            compressor, pitch, chorus, flanger
  mix       mirrors the 60-schematic golden set (corpus 298 gif/157 pdf/109 jpg/16 png;
            confidence 20 high/28 medium/12 low) scaled to 12:
            gif 5-7 · pdf 2-4 · jpg 1-3 · png 1 · high 3-5 · medium 4-6 · low 2-3 ·
            >= 3 lint `netlist-candidate` (so nets can be scored, not only parts)

Deterministic for a given --seed. Outputs (local-only; they name third-party schematics):
  <out>/pilot-12.csv   <out>/<slug>.<ext>  (copy of the source image)
  <out>/<slug>.truth.csv  (blank: ref,type,value — fill from the IMAGE, not the extraction)
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lint_extractions import lint_dir  # noqa: E402

SLOTS = ["fuzz", "fuzz", "distortion", "distortion", "filter", "delay", "eq",
         "phaser", "compressor", "pitch", "chorus", "flanger"]
EXCLUDE_TYPES = {"utility", "modification"}
# Obvious non-pedals that the scrape filed under effect types (voice-recorder ICs, speech chips).
# Replace with the D0 triage classes (COMMERCIAL/DIY/CLONE) once that chat has been run.
NOT_PEDAL_HINT = re.compile(r"recorder|speak-and|voice")


HOWTO = """PILOT TRUTH SHEETS — how to fill them in
=========================================
Goal: a trustworthy answer key made from the IMAGE, so the extractor can be graded.
Do NOT open the extraction JSON or the KiCad project while you do this.

For each <slug>.<png|gif|jpg|pdf> open <slug>.truth.csv (a spreadsheet app or any text
editor) and add one row per part, columns:  ref,type,value

  ref    as printed on the drawing (R1, C3, Q2, RV1). If the drawing prints NO reference,
         leave it blank — the scorer still counts the part by type + value.
  type   resistor | capacitor | potentiometer | transistor | diode | led | opamp | ic
  value  as printed, any style is fine (4k7, 4.7k, 100n, .1uf, 47p, 100kA, 2N3904, TL072).
         Pots: include the taper if shown (A / B / LOG / LIN). Unreadable: write ? .
  skip   jacks, switches, battery, wiring, enclosure, LED resistors you cannot see — only the
         types above are scored.

Tips: one schematic at a time is fine (blank sheets are skipped). Order does not matter.
Do the three that have a <slug>.nets.csv last, if you have the energy: add one row per net,
columns  net,pins   with pins as space-separated REF.PIN, e.g.
  input,C1.1 R1.1 Q1.B        (pin = the leg: B/C/E for a transistor, 1/2 for a resistor...)
These three are the only ones whose connectivity is complete enough to be scored; skip the
nets files entirely if you only want the parts score.

When you are done (or partway — it scores whatever is filled in), tell Claude Code
"score the pilot". It runs:
  python3 pipeline/tools/score_pilot.py --pilot docs/research/pilot --extractions <extractions dir>
"""


def build_pool(manifest_json: Path, extractions: Path) -> list[dict]:
    entries = json.loads(manifest_json.read_text())["entries"]
    slug_count = Counter(e["slug"] for e in entries.values())
    lint = {r["slug"]: r for r in lint_dir(extractions)}
    pool = []
    for path, e in entries.items():
        slug = e["slug"]
        r = lint.get(slug)
        if (r is None or r["tier"] in ("no-parts", "unreadable", "suspect-no-schematic")
                or slug_count[slug] > 1):
            continue
        if not 10 <= r["parts"] <= 80 or e.get("effect_type") in EXCLUDE_TYPES:
            continue
        if NOT_PEDAL_HINT.search(slug):               # stopgap until the D0 triage classifies rows
            continue
        if not Path(path).is_file():
            continue
        pool.append({"slug": slug, "name": e["name"], "effect_type": e["effect_type"],
                     "file_type": e["file_type"], "path": path, "parts": r["parts"],
                     "pin_coverage": r["pin_coverage"], "tier": r["tier"],
                     "confidence": r["confidence"]})
    return pool


def acceptable(pick: list[dict]) -> bool:
    ft = Counter(p["file_type"] for p in pick)
    conf = Counter(p["confidence"] for p in pick)
    cand = sum(1 for p in pick if p["tier"] == "netlist-candidate")
    return (ft["png"] == 1 and 5 <= ft["gif"] <= 7 and 2 <= ft["pdf"] <= 4
            and 1 <= ft["jpg"] <= 3 and 3 <= conf["high"] <= 5
            and 4 <= conf["medium"] <= 6 and 2 <= conf["low"] <= 3 and cand >= 3)


def pick(pool: list[dict], seed: int, tries: int = 2_000_000) -> tuple[list[dict], int]:
    rng = random.Random(seed)
    by_type: dict[str, list[dict]] = {}
    for p in pool:
        by_type.setdefault(p["effect_type"], []).append(p)
    need = Counter(SLOTS)
    for t, n in need.items():
        if len(by_type.get(t, [])) < n:
            raise SystemExit(f"pool too small for {t}: {len(by_type.get(t, []))} < {n}")
    for i in range(1, tries + 1):
        chosen = []
        for t, n in need.items():
            chosen += rng.sample(by_type[t], n)
        if acceptable(chosen):
            return chosen, i
    raise SystemExit("no draw satisfied the constraints; relax them")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--manifest-json", required=True, help="pipeline/manifest.json")
    ap.add_argument("--extractions", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261111)
    args = ap.parse_args()

    pool = build_pool(Path(args.manifest_json), Path(args.extractions))
    chosen, n = pick(pool, args.seed)
    chosen.sort(key=lambda p: (SLOTS.index(p["effect_type"]), p["slug"]))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cols = ["slug", "name", "effect_type", "file_type", "parts", "confidence", "tier", "pin_coverage"]
    with open(out / "pilot-12.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(chosen)
    for p in chosen:
        src = Path(p["path"])
        shutil.copy2(src, out / f"{p['slug']}{src.suffix.lower()}")
        sheet = out / f"{p['slug']}.truth.csv"
        if not sheet.exists():                        # never overwrite hand-entered truth
            sheet.write_text("ref,type,value\n")
        if p["tier"] == "netlist-candidate":          # nets are only scorable where lint passes
            nets = out / f"{p['slug']}.nets.csv"
            if not nets.exists():
                nets.write_text("net,pins\n")
    howto = out / "HOW-TO.txt"
    if not howto.exists():
        howto.write_text(HOWTO)
    print(f"pool {len(pool)} · seed {args.seed} · accepted draw #{n}")
    for p in chosen:
        print(f"  {p['effect_type']:<11} {p['file_type']:<4} {p['parts']:>3} parts  "
              f"{p['confidence']:<6} {p['tier']:<17} {p['slug']}")
    ft = Counter(p["file_type"] for p in chosen)
    cf = Counter(p["confidence"] for p in chosen)
    print(f"mix: {dict(ft)} · confidence {dict(cf)} · "
          f"{sum(p['tier'] == 'netlist-candidate' for p in chosen)} netlist-candidates · "
          f"{sum(p['parts'] for p in chosen)} parts to read")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
