#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Cut the schematic manifest into census batches (one research chat each).

Input  : docs/research/schematic-manifest.csv  (slug,name,source_category,effect_type,file_type,state)
Output : <out>/B01.csv … Bnn.csv  +  <out>/census-batches.csv (slug → batch)

Batches are grouped by effect_type in a fixed priority order (simple, well-documented,
most-likely-to-be-built first), alphabetical by slug inside a type so same-maker entries
stay together. Rows are split into balanced chunks of at most --size; small adjacent
chunks of different types are merged when they still fit.

Re-run after the D0 triage chat: pass its CSV with --triage to drop rows whose class is
in --drop (default NOT-CIRCUIT, WIRING). The 16 slugs that occur twice in the manifest
keep BOTH rows so the research chat sees both files.

The outputs list third-party schematic titles — keep them local (docs/research/census/
is gitignored).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

ORDER = ["fuzz", "distortion", "compressor", "phaser", "tremolo", "reverb", "chorus",
         "flanger", "delay", "filter", "eq", "pitch", "ring_mod", "utility", "modification"]


def balanced(rows: list[dict], size: int) -> list[list[dict]]:
    k = max(1, math.ceil(len(rows) / size))
    per, extra = divmod(len(rows), k)
    out, i = [], 0
    for j in range(k):
        n = per + (1 if j < extra else 0)
        out.append(rows[i:i + n])
        i += n
    return out


def make_batches(rows: list[dict], size: int) -> list[list[dict]]:
    types = ORDER + sorted({r["effect_type"] for r in rows} - set(ORDER))
    chunks: list[list[dict]] = []
    for t in types:
        grp = sorted((r for r in rows if r["effect_type"] == t), key=lambda r: (r["slug"], r["source_category"]))
        if grp:
            chunks.extend(balanced(grp, size))
    merged: list[list[dict]] = []
    for c in chunks:
        if merged and len(merged[-1]) + len(c) <= size and merged[-1][-1]["effect_type"] != c[0]["effect_type"]:
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)
    return merged


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=15, help="max rows per batch (default 15)")
    ap.add_argument("--triage", help="D0 triage CSV with columns slug,class")
    ap.add_argument("--drop", default="NOT-CIRCUIT,WIRING", help="comma list of D0 classes to drop")
    ap.add_argument("--extractions", help="extractions/ dir; also writes Bxx-extractions.json "
                    "(slug -> extraction) so the chat can diff against our machine-read data")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.manifest)))
    if args.triage:
        drop = {c.strip().upper() for c in args.drop.split(",")}
        klass = {r["slug"]: r["class"].strip().upper() for r in csv.DictReader(open(args.triage))}
        before = len(rows)
        rows = [r for r in rows if klass.get(r["slug"], "") not in drop]
        print(f"triage dropped {before - len(rows)} rows ({', '.join(sorted(drop))})")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in (list(out.glob("B[0-9][0-9].csv")) + list(out.glob("B[0-9][0-9]-extractions.json"))
                + list(out.glob("census-batches.csv"))):
        old.unlink()                                  # derived files; always regenerated

    batches = make_batches(rows, args.size)
    cols = ["slug", "name", "source_category", "effect_type", "file_type", "state", "batch"]
    index = []
    for i, b in enumerate(batches, 1):
        name = f"B{i:02d}"
        with open(out / f"{name}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in b:
                w.writerow({**r, "batch": name})
                index.append({**r, "batch": name})
        if args.extractions:
            bundle, missing = {}, []
            for r in b:
                f = Path(args.extractions) / f"{r['slug']}.json"
                if f.exists():
                    bundle[r["slug"]] = json.loads(f.read_text())
                else:
                    missing.append(r["slug"])
            (out / f"{name}-extractions.json").write_text(json.dumps(bundle, indent=1))
            if missing:
                print(f"  {name}: no extraction for {', '.join(missing)}")
    with open(out / "census-batches.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(index)

    print(f"{len(rows)} rows -> {len(batches)} batches of <= {args.size}")
    for i, b in enumerate(batches, 1):
        kinds = "+".join(dict.fromkeys(r["effect_type"] for r in b))
        print(f"  B{i:02d}  {kinds:<22} {len(b)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
