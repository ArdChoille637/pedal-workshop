#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Structural lint for schematic extractions (`extractions/<slug>.json`).

WHY: the extractions were produced by a vision model in one pass and never
checked against anything. This script measures what can be measured WITHOUT
ground truth — internal consistency — and turns "574 awaiting review" into a
ranked queue. It does NOT measure whether a value was read correctly; that needs
the golden set (docs/handoff-fable-review-and-research.md, reply §2.4).

What it checks, per schematic:
  pin_coverage     pins placed in a net ÷ pins the parts declare (0..1)
  zero_nets        no nets at all (parts list only)
  unconnected      parts that appear in no net
  dangling_refs    net pins that name a part which does not exist
  dup_refs         duplicate reference designators
  single_pin_nets  nets with one pin (connect nothing)
  multi_net_pins   (ref, pin) that appear in more than one net (shorts / mis-traces)
  off_e24          resistor/capacitor values that parse but are not E24 (review queue —
                   legitimate odd values and misreads both land here)
  value_issues     R/C values that cannot be parsed to a number; split into
                   vals_ok / vals_assumed (bare resistor number = ohms) /
                   vals_ambiguous (e.g. ".022", "1/50": never guessed) / vals_unknown

Tier (what the data may be used for):
  netlist-candidate  pin_coverage >= 0.95, no dangling refs, no duplicate refs
  parts-list-only    has parts but fails the above — usable only as an unverified parts list
  no-parts           zero parts (not an extractable analog circuit)

Usage:
  python3 lint_extractions.py                      # summary for ./extractions
  python3 lint_extractions.py --csv lint.csv       # + one row per schematic
  python3 lint_extractions.py --dir path/to/extractions
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6,
       3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]

CANDIDATE_COVERAGE = 0.95

# ── value parsing ────────────────────────────────────────────────────────────
# Deliberately conservative: anything not clearly one number+unit is "ambiguous"
# or "unknown" — never guessed. Statuses: ok | assumed-unit | ambiguous | unknown.

_SI = {"p": 1e-12, "P": 1e-12, "n": 1e-9, "N": 1e-9, "u": 1e-6, "U": 1e-6,
       "µ": 1e-6, "μ": 1e-6, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "r": 1.0, "R": 1.0}
_SYMS = "pPnNuUµμkKMGrR"
_JUNK = re.compile(r"\s*(ohms?|Ω|Ω|ω|farads?)\b|[Ω]", re.IGNORECASE)
_RKM = re.compile(rf"^(\d+)([{_SYMS}])(\d+)([fF])?$")           # 4k7, 2u2, 4n7, 1r5
_PLAIN = re.compile(rf"^(\d*\.?\d+)(meg|MEG|Meg|[{_SYMS}])?([fF])?$")


def parse_value(raw: str | None, kind: str) -> tuple[float | None, str]:
    """Return (numeric value in base units, status). kind: 'resistor' | 'capacitor'."""
    if raw is None:
        return None, "unknown"
    s = str(raw).strip()
    if not s or s.lower() in {"unknown", "not specified", "(unlabeled)", "n/a", "?", "-"}:
        return None, "unknown"
    volt = re.match(r"^(.+?)\s*/\s*(\d+(?:\.\d+)?)\s*v?$", s, re.IGNORECASE)
    if volt and re.search(r"[pPnNuUµμ]|\d[fF]$", volt.group(1)):
        s = volt.group(1)                            # "10u/16V": keep the value, drop the rating
    if re.search(r"\bor\b|/|\*|\?|~|\bto\b|[,;]", s, re.IGNORECASE):
        return None, "ambiguous"
    s = _JUNK.sub("", s).strip()
    s = s.split()[0] if s.split() else ""            # "10uF 50v" -> "10uF"
    s = s.rstrip("%").replace("±", "")
    if not s:
        return None, "unknown"

    m = _RKM.match(s)
    if m:
        whole, sym, frac, _f = m.groups()
        num = float(f"{whole}.{frac}") * _SI[sym]
        return _kind_check(num, sym, kind)
    if re.match(r"^(\d*\.?\d+)m[fF]?$", s):
        return None, "ambiguous"                     # "1m": milli, mega, or legacy "mF" = uF?
    m = _PLAIN.match(s)
    if not m:
        return None, "unknown"
    mant, sym, _f = m.groups()
    mant = float(mant)
    if sym is None:
        if kind == "resistor":
            return mant, "assumed-unit"              # bare number = ohms by convention
        return None, "ambiguous"                     # ".022", "100": uF or pF? never guess
    if sym.lower() == "meg":
        return mant * 1e6, "ok"
    return _kind_check(mant * _SI[sym], sym, kind)


def _kind_check(num: float, sym: str, kind: str) -> tuple[float | None, str]:
    if kind == "resistor" and sym in "pPnNuUµμ":
        return None, "ambiguous"                     # picoohms are not a thing: misread
    if kind == "capacitor" and sym in "kKMGrR":
        return None, "ambiguous"
    return num, "ok"


def is_e24(num: float, rel_tol: float = 1e-4) -> bool:
    # rel_tol only absorbs float error: parsed decimals are exact, so 6.205 is NOT 6.2.
    if num is None or num <= 0:
        return False
    exp = math.floor(math.log10(num))
    mant = round(num / (10 ** exp), 6)
    if mant >= 10:
        mant, exp = mant / 10, exp + 1
    return any(abs(mant - e) / e <= rel_tol for e in E24 + [10.0])


# ── per-schematic lint ───────────────────────────────────────────────────────

def split_pin(token: str) -> tuple[str, str]:
    ref, _, pin = str(token).strip().rpartition(".")
    if not ref:                                      # no dot: whole token is the ref
        return pin, ""
    return ref, pin


def lint(doc: dict) -> dict:
    parts = doc.get("parts") or []
    nets = doc.get("nets") or []
    refs = [p.get("ref") for p in parts]
    ref_set = set(refs)
    declared = {p.get("ref"): int(p.get("pins") or 0) for p in parts}

    placed: dict[str, set[str]] = {}
    pin_nets: dict[tuple[str, str], int] = Counter()
    dangling = single = 0
    for n in nets:
        pins = n.get("pins") or []
        if len(pins) == 1:
            single += 1
        for tok in set(pins):                        # a pin listed twice in one net counts once
            ref, pin = split_pin(tok)
            pin_nets[(ref, pin)] += 1
            if ref not in ref_set:
                dangling += 1
            else:
                placed.setdefault(ref, set()).add(pin)

    decl_total = sum(v for v in declared.values() if v > 0)
    placed_total = sum(min(len(placed.get(r, ())), d) for r, d in declared.items() if d > 0)
    coverage = (placed_total / decl_total) if decl_total else 0.0

    off_e24 = 0
    value_issues = 0
    vstat: Counter = Counter()
    for p in parts:
        kind = {"resistor": "resistor", "capacitor": "capacitor"}.get(p.get("type"))
        if not kind:
            continue
        num, status = parse_value(p.get("value"), kind)
        vstat[status] += 1
        if num is None:
            value_issues += 1
        elif not is_e24(num):
            off_e24 += 1

    row = {
        "parts": len(parts),
        "nets": len(nets),
        "pins_declared": decl_total,
        "pins_placed": placed_total,
        "pin_coverage": round(coverage, 4),
        "zero_nets": int(len(nets) == 0),
        "unconnected": sum(1 for r in ref_set if r not in placed),
        "dangling_refs": dangling,
        "dup_refs": len(refs) - len(ref_set),
        "single_pin_nets": single,
        "multi_net_pins": sum(1 for v in pin_nets.values() if v > 1),
        "off_e24": off_e24,
        "value_issues": value_issues,
        "vals_ok": vstat["ok"], "vals_assumed": vstat["assumed-unit"],
        "vals_ambiguous": vstat["ambiguous"], "vals_unknown": vstat["unknown"],
        "confidence": doc.get("confidence", ""),
        "issues": len(doc.get("issues") or []),
    }
    if not parts:
        row["tier"] = "no-parts"
    elif coverage >= CANDIDATE_COVERAGE and not dangling and not row["dup_refs"]:
        row["tier"] = "netlist-candidate"
    else:
        row["tier"] = "parts-list-only"
    return row


def lint_dir(path: Path) -> list[dict]:
    rows = []
    for f in sorted(path.glob("*.json")):
        try:
            doc = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError) as e:
            rows.append({"slug": f.stem, "tier": "unreadable", "error": str(e)})
            continue
        rows.append({"slug": f.stem, **lint(doc)})
    return rows


def summarize(rows: list[dict]) -> str:
    ok = [r for r in rows if r["tier"] != "unreadable"]
    n = len(ok)
    parts = sum(r["parts"] for r in ok)
    unconn = sum(r["unconnected"] for r in ok)
    dec = sum(r["pins_declared"] for r in ok)
    pl = sum(r["pins_placed"] for r in ok)
    cov = [r["pin_coverage"] for r in ok if r["parts"]]
    tiers = Counter(r["tier"] for r in rows)
    conf = Counter(r["confidence"] for r in ok)
    out = [
        f"schematics            {len(rows)}  (unreadable: {tiers.get('unreadable', 0)})",
        f"parts                 {parts}",
        f"zero-net schematics   {sum(r['zero_nets'] for r in ok)}",
        f"unconnected parts     {unconn}  ({unconn / parts:.0%})" if parts else "unconnected parts     -",
        f"pin coverage (pooled) {pl}/{dec} = {pl / dec:.0%}" if dec else "pin coverage          -",
        f"pin coverage (median) {statistics.median(cov):.0%}" if cov else "",
        f"  under 50%           {sum(1 for c in cov if c < 0.5)}",
        f"  at least 95%        {sum(1 for c in cov if c >= CANDIDATE_COVERAGE)}",
        f"dangling net refs     {sum(r['dangling_refs'] for r in ok)}",
        f"duplicate refs        {sum(r['dup_refs'] for r in ok)}",
        f"single-pin nets       {sum(r['single_pin_nets'] for r in ok)}",
        f"multi-net pins        {sum(r['multi_net_pins'] for r in ok)}",
        f"off-E24 R/C values    {sum(r['off_e24'] for r in ok)}",
        "R/C values            ok {} · assumed-unit {} · ambiguous {} · unknown {}".format(
            *(sum(r[k] for r in ok) for k in ("vals_ok", "vals_assumed", "vals_ambiguous", "vals_unknown"))),
        f"tiers                 {dict(tiers)}",
        f"extractor confidence  {dict(conf)}",
    ]
    return "\n".join(line for line in out if line)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", default=str(Path(__file__).parent / "extractions"))
    ap.add_argument("--csv", help="write one row per schematic to this path")
    args = ap.parse_args(argv)
    path = Path(args.dir)
    if not path.is_dir():
        print(f"no such directory: {path}", file=sys.stderr)
        return 2
    rows = lint_dir(path)
    print(summarize(rows))
    if args.csv:
        cols = ["slug", "tier", "parts", "nets", "pins_declared", "pins_placed", "pin_coverage",
                "zero_nets", "unconnected", "dangling_refs", "dup_refs", "single_pin_nets",
                "multi_net_pins", "off_e24", "value_issues", "vals_ok", "vals_assumed",
                "vals_ambiguous", "vals_unknown", "confidence", "issues"]
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: (r.get("pin_coverage", 0), r["slug"])))
        print(f"wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
