#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Score extractions against hand-made truth sheets (the pilot / golden set).

Protocol: docs/fable-reply-v1.md §2.4, with the revised tiers in
docs/handoff-fable-review-and-research.md (v3).

INPUT  (a folder, e.g. docs/research/pilot/)
  <slug>.truth.csv   ref,type,value        — read from the IMAGE, never from the extraction
  <slug>.nets.csv    net,pins              — optional; pins space-separated REF.PIN; only for
                                             lint `netlist-candidate` schematics
  Blank sheets are skipped. Only R, C, pots, transistors/diodes/LEDs/op-amps/ICs are scored;
  jacks, switches, batteries etc. are ignored on BOTH sides.

WHAT IT MEASURES (fidelity: did the extractor read THIS image correctly?)
  BOM recall / precision   multiset of (class, canonical value) — what you would actually order;
                           independent of reference designators (extractors invent refs when the
                           drawing has none)
  value accuracy           on parts whose ref matches: R/C/P by NUMERIC value (4k7 = 4.7k,
                           100n = .1uf), semis by part-number identity (324 ~ LM324). `strict`
                           counts a bare-number cap (".022" vs "22n") as wrong, `lenient` as right
  pot taper                only where both sides state it
  net F1                   over pin-pairs that share a net (candidates with a nets sheet only)
  calibration              the same numbers split by the extractor's own confidence
All ratios carry a 95% interval from a bootstrap over SCHEMATICS (errors cluster per drawing).
It does NOT measure correctness of the drawing itself (wrong circuit under the title) — that is
the census (docs/census-prompt-d1-v2.md).

  python3 score_pilot.py --pilot docs/research/pilot --extractions <extractions dir> [--csv diff.csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lint_extractions import lint, parse_value  # noqa: E402

# ── thresholds (handoff v3 "Revised ship tiers") ─────────────────────────────
STOP_BELOW = 0.90                      # point estimate of recall / passive value accuracy
BADGE_LOWER = {"recall": 0.90, "precision": 0.90, "passive": 0.90, "semi": 0.95}
NET_F1_SHIP = 0.95
BOOT_N = 2000

# ── part classes ─────────────────────────────────────────────────────────────
_CLASS = {
    "resistor": "R", "res": "R", "r": "R",
    "capacitor": "C", "cap": "C", "c": "C", "electrolytic": "C", "tantalum": "C",
    "potentiometer": "P", "pot": "P", "trimmer": "P", "trim": "P", "trimpot": "P", "vr": "P",
}
_SEMI = {"transistor", "jfet", "mosfet", "bjt", "npn", "pnp", "fet", "q", "diode", "d", "led",
         "zener", "opamp", "op-amp", "op amp", "ic", "chip", "ota", "regulator", "photocell",
         "ldr", "optocoupler", "vactrol"}


def part_class(t: str | None) -> str | None:
    t = (t or "").strip().lower()
    if t in _CLASS:
        return _CLASS[t]
    return "S" if t in _SEMI else None


# ── value keys ───────────────────────────────────────────────────────────────
# "10k LIN", "100kA" (letter after the number/unit), "B10k" (letter before the number)
_TAPER = re.compile(r"\b(lin|log|rev)\b|(?<=[\dkKMmR.])([abc])\b|\b([abc])(?=\d)", re.IGNORECASE)
_TAPER_MAP = {"lin": "B", "log": "A", "rev": "C", "a": "A", "b": "B", "c": "C"}
_BARE = re.compile(r"^\s*(\d*\.?\d+)\s*$")


def taper_of(raw: str | None) -> str | None:
    m = _TAPER.search(raw or "")
    if not m:
        return None
    return _TAPER_MAP[next(g for g in m.groups() if g).lower()]


def strip_taper(raw: str | None) -> str:
    return _TAPER.sub("", raw or "").strip()


def _sig(num: float) -> float:
    return float(f"{num:.6g}")


def value_compare(cls: str, a: str | None, b: str | None) -> str:
    """'match' | 'unit-ambiguous' | 'wrong' for R/C/P values."""
    kind = "capacitor" if cls == "C" else "resistor"
    na, sa = parse_value(strip_taper(a) if cls == "P" else a, kind)
    nb, sb = parse_value(strip_taper(b) if cls == "P" else b, kind)
    if na is not None and nb is not None:
        return "match" if _sig(na) == _sig(nb) else "wrong"
    ma = _BARE.match(strip_taper(a) if cls == "P" else a or "")
    mb = _BARE.match(strip_taper(b) if cls == "P" else b or "")
    if ma and mb:                                      # both bare numbers (".022" vs "0.022")
        return "match" if _sig(float(ma.group(1))) == _sig(float(mb.group(1))) else "wrong"
    for bare, other in ((ma, nb), (mb, na)):           # bare ".022" vs parsed "22n"
        if bare and other is not None and cls == "C":
            if _sig(float(bare.group(1)) * 1e-6) == _sig(other):
                return "unit-ambiguous"
    return "wrong"


def _ident(raw: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (raw or "").upper())


def semi_compare(a: str | None, b: str | None) -> str:
    x, y = _ident(a), _ident(b)
    if not x or not y:
        return "wrong"
    if x == y:
        return "match"
    short, long_ = sorted((x, y), key=len)
    if len(short) >= 3 and long_.endswith(short):
        return "match"                                  # "LM324" ~ "324" (alias, same identity)
    return "wrong"


def bag_key(cls: str, raw: str | None):
    if cls == "S":
        return ("S", _ident(raw))
    kind = "capacitor" if cls == "C" else "resistor"
    num, _ = parse_value(strip_taper(raw) if cls == "P" else raw, kind)
    if num is not None:
        return (cls, _sig(num))
    m = _BARE.match(strip_taper(raw) if cls == "P" else raw or "")
    if m:
        return (cls, ("bare", _sig(float(m.group(1)))))
    return (cls, ("str", re.sub(r"\s+", "", (raw or "").lower())))


# ── scoring one schematic ────────────────────────────────────────────────────

def read_truth(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
            if not (r.get("type") or r.get("value") or r.get("ref")):
                continue
            cls = part_class(r.get("type"))
            if cls:
                rows.append({"ref": r.get("ref", "").upper().replace(" ", ""), "cls": cls,
                             "type": r.get("type", ""), "value": r.get("value", "")})
    return rows


def read_nets(path: Path) -> list[set[str]]:
    nets = []
    if not path.exists():
        return nets
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            pins = {p.strip().upper() for p in (r.get("pins") or "").split() if p.strip()}
            if len(pins) >= 2:
                nets.append(pins)
    return nets


def pairs(nets) -> set[tuple[str, str]]:
    out = set()
    for n in nets:
        for a, b in combinations(sorted(n), 2):
            out.add((a, b))
    return out


def score_one(slug: str, truth: list[dict], doc: dict, truth_nets: list[set[str]]) -> dict:
    ext = []
    for p in doc.get("parts") or []:
        cls = part_class(p.get("type"))
        if cls:
            ext.append({"ref": str(p.get("ref") or "").upper().replace(" ", ""), "cls": cls,
                        "type": p.get("type", ""), "value": str(p.get("value") or "")})

    # BOM bag
    tb = Counter(bag_key(t["cls"], t["value"]) for t in truth)
    eb = Counter(bag_key(e["cls"], e["value"]) for e in ext)
    hit = tb & eb
    by_cls = {c: {"truth": sum(1 for t in truth if t["cls"] == c),
                  "ext": sum(1 for e in ext if e["cls"] == c),
                  "hit": sum(v for k, v in hit.items() if k[0] == c)} for c in "RCPS"}

    # Ref-level
    ext_by_ref: dict[str, dict] = {}
    for e in ext:
        ext_by_ref.setdefault(e["ref"], e)
    diff, ref_matched = [], 0
    vstat = {"passive": [0, 0, 0], "semi": [0, 0], "taper": [0, 0]}   # strict ok, lenient ok, den
    for t in truth:
        e = ext_by_ref.get(t["ref"]) if t["ref"] else None
        if e is None:
            diff.append({"slug": slug, "ref": t["ref"], "truth_type": t["type"], "truth_value": t["value"],
                         "ext_type": "", "ext_value": "", "verdict": "missing-in-extraction"})
            continue
        ref_matched += 1
        if t["cls"] != e["cls"]:
            verdict = "type-wrong"
        elif t["cls"] == "S":
            verdict = semi_compare(t["value"], e["value"])
            vstat["semi"][1] += 1
            vstat["semi"][0] += verdict == "match"
        else:
            verdict = value_compare(t["cls"], t["value"], e["value"])
            vstat["passive"][2] += 1
            vstat["passive"][0] += verdict == "match"
            vstat["passive"][1] += verdict in ("match", "unit-ambiguous")
            if t["cls"] == "P" and taper_of(t["value"]) and taper_of(e["value"]):
                vstat["taper"][1] += 1
                vstat["taper"][0] += taper_of(t["value"]) == taper_of(e["value"])
        if verdict == "wrong":
            verdict = "value-wrong"
        diff.append({"slug": slug, "ref": t["ref"], "truth_type": t["type"], "truth_value": t["value"],
                     "ext_type": e["type"], "ext_value": e["value"], "verdict": verdict})
    truth_refs = {t["ref"] for t in truth if t["ref"]}
    for e in ext:
        if e["ref"] and e["ref"] not in truth_refs:
            diff.append({"slug": slug, "ref": e["ref"], "truth_type": "", "truth_value": "",
                         "ext_type": e["type"], "ext_value": e["value"], "verdict": "extra-in-extraction"})

    # Nets
    net = None
    lint_tier = lint(doc)["tier"]
    if truth_nets and lint_tier == "netlist-candidate":
        tp_pairs = pairs(truth_nets)
        ep = pairs([{p.upper() for p in (n.get("pins") or [])} for n in (doc.get("nets") or [])])
        net = {"tp": len(tp_pairs & ep), "fp": len(ep - tp_pairs), "fn": len(tp_pairs - ep)}

    return {"slug": slug, "confidence": doc.get("confidence", ""), "tier": lint_tier,
            "truth_n": len(truth), "ext_n": len(ext), "hit": sum(hit.values()),
            "ref_matched": ref_matched, "by_cls": by_cls, "vstat": vstat, "net": net, "diff": diff}


# ── pooling + bootstrap ──────────────────────────────────────────────────────

def _ratio(rows: list[dict], num, den) -> float | None:
    d = sum(den(r) for r in rows)
    return sum(num(r) for r in rows) / d if d else None


METRICS = {
    "recall":    (lambda r: r["hit"], lambda r: r["truth_n"]),
    "precision": (lambda r: r["hit"], lambda r: r["ext_n"]),
    "passive_strict":  (lambda r: r["vstat"]["passive"][0], lambda r: r["vstat"]["passive"][2]),
    "passive_lenient": (lambda r: r["vstat"]["passive"][1], lambda r: r["vstat"]["passive"][2]),
    "semi":      (lambda r: r["vstat"]["semi"][0], lambda r: r["vstat"]["semi"][1]),
    "taper":     (lambda r: r["vstat"]["taper"][0], lambda r: r["vstat"]["taper"][1]),
    "ref_match": (lambda r: r["ref_matched"], lambda r: r["truth_n"]),
    **{f"recall_{c}": ((lambda r, c=c: r["by_cls"][c]["hit"]), (lambda r, c=c: r["by_cls"][c]["truth"]))
       for c in "RCPS"},
}


def net_f1(rows: list[dict]) -> float | None:
    n = [r["net"] for r in rows if r["net"]]
    if not n:
        return None
    tp, fp, fn = (sum(x[k] for x in n) for k in ("tp", "fp", "fn"))
    return (2 * tp) / (2 * tp + fp + fn) if (2 * tp + fp + fn) else None


def bootstrap(rows: list[dict], fn, seed: int = 1, n: int = BOOT_N) -> tuple[float | None, float | None]:
    if len(rows) < 2:
        return None, None
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        v = fn([rows[rng.randrange(len(rows))] for _ in rows])
        if v is not None:
            vals.append(v)
    if not vals:
        return None, None
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))]


def summarize(rows: list[dict]) -> dict:
    out = {}
    for name, (num, den) in METRICS.items():
        f = lambda rs, num=num, den=den: _ratio(rs, num, den)  # noqa: E731
        out[name] = (f(rows), *bootstrap(rows, f))
    out["net_f1"] = (net_f1(rows), *bootstrap([r for r in rows if r["net"]], net_f1))
    return out


# ── driver ───────────────────────────────────────────────────────────────────

def score_dir(pilot: Path, extractions: Path) -> list[dict]:
    rows = []
    for tf in sorted(pilot.glob("*.truth.csv")):
        slug = tf.name[: -len(".truth.csv")]
        truth = read_truth(tf)
        if not truth:
            continue
        ef = extractions / f"{slug}.json"
        if not ef.exists():
            print(f"  ! no extraction for {slug}", file=sys.stderr)
            continue
        rows.append(score_one(slug, truth, json.loads(ef.read_text()), read_nets(pilot / f"{slug}.nets.csv")))
    return rows


def pct(v) -> str:
    return "  n/a" if v is None else f"{v:5.1%}"


def interval(t) -> str:
    v, lo, hi = t
    return f"{pct(v)}  [{pct(lo).strip()} – {pct(hi).strip()}]" if lo is not None else f"{pct(v)}  [n too small]"


def report(rows: list[dict], pilot: Path, extractions: Path) -> str:
    sheets = sorted(pilot.glob("*.truth.csv"))
    out = [f"scored {len(rows)} of {len(sheets)} truth sheets (blank sheets skipped)"]
    if not rows:
        return "\n".join(out + ["nothing to score yet — fill in the <slug>.truth.csv sheets first."])
    s = summarize(rows)
    use_bag = (s["ref_match"][0] or 0) < 0.8
    out += ["", f"{'metric':<34}{'estimate  [95% interval over schematics]'}", "-" * 72]
    names = [("recall", "BOM recall (all scored parts)"), ("precision", "BOM precision"),
             ("recall_R", "  recall — resistors"), ("recall_C", "  recall — capacitors"),
             ("recall_P", "  recall — pots"), ("recall_S", "  recall — semis / ICs"),
             ("passive_strict", "value accuracy R/C/P (strict)"), ("passive_lenient", "value accuracy R/C/P (lenient)"),
             ("semi", "semiconductor identity"), ("taper", "pot taper (both stated)"),
             ("ref_match", "ref designators matching"), ("net_f1", "net F1 (netlist-candidates)")]
    for k, label in names:
        out.append(f"{label:<34}{interval(s[k])}")
    if use_bag:
        out.append("\n! under 80% of truth refs match the extraction's refs (it may have invented refs); "
                   "passive accuracy below falls back to BOM recall of R/C/P.")
        rcp = [r for r in rows]
        num = lambda r: sum(r["by_cls"][c]["hit"] for c in "RCP")      # noqa: E731
        den = lambda r: sum(r["by_cls"][c]["truth"] for c in "RCP")    # noqa: E731
        bag = _ratio(rcp, num, den)
        s["_bag_passive"] = bag
        out.append(f"  BOM recall of R/C/P: {pct(bag)}")
    out += ["", "calibration — does the extractor's own confidence mean anything?",
            f"{'confidence':<12}{'n':>3}{'BOM recall':>12}{'precision':>11}"]
    for c in ("high", "medium", "low"):
        sub = [r for r in rows if r["confidence"] == c]
        if sub:
            out.append(f"{c:<12}{len(sub):>3}{pct(_ratio(sub, *METRICS['recall'])):>12}"
                       f"{pct(_ratio(sub, *METRICS['precision'])):>11}")
    out += ["", "per schematic (worst first)", f"{'slug':<42}{'conf':<8}{'truth':>6}{'ext':>5}{'recall':>8}{'prec':>7}"]
    for r in sorted(rows, key=lambda r: r["hit"] / max(r["truth_n"], 1)):
        out.append(f"{r['slug']:<42}{r['confidence']:<8}{r['truth_n']:>6}{r['ext_n']:>5}"
                   f"{pct(r['hit'] / r['truth_n'] if r['truth_n'] else None):>8}"
                   f"{pct(r['hit'] / r['ext_n'] if r['ext_n'] else None):>7}")
    verdicts = Counter(d["verdict"] for r in rows for d in r["diff"])
    out += ["", "ref-level verdicts: " + ", ".join(f"{k} {v}" for k, v in sorted(verdicts.items()))]
    nf = s["net_f1"][0]
    if nf is not None:
        out.append(f"nets: F1 {nf:.2f} — {'meets' if nf >= NET_F1_SHIP else 'below'} the {NET_F1_SHIP:.2f} bar "
                   f"({sum(1 for r in rows if r['net'])} schematic(s) scored)")
    out += ["", "VERDICT (handoff v3 tiers):"] + ["  " + v for v in _verdict(s, len(rows), use_bag)]
    out.append("\nNote: fidelity only (extraction vs the image we hold). A perfect score here says nothing "
               "about the image being the right circuit — that is the census.")
    return "\n".join(out)


def _verdict(s: dict, n: int, use_bag: bool) -> list[str]:
    rec = s["recall"]
    passive_point = s.get("_bag_passive") if use_bag else s["passive_strict"][0]
    passive_lo = None if use_bag else s["passive_strict"][1]
    if rec[0] is None or passive_point is None:
        return ["INCONCLUSIVE — not enough scored parts yet."]
    if rec[0] < STOP_BELOW or passive_point < STOP_BELOW:
        return [f"STOP — recall {rec[0]:.0%}, passive value accuracy {passive_point:.0%} "
                f"(below {STOP_BELOW:.0%}). Re-extract with a second engine before reviewing more."]
    lo = lambda t: t[1] if t[1] is not None else 0.0  # noqa: E731
    ok = (lo(s["recall"]) >= BADGE_LOWER["recall"] and lo(s["precision"]) >= BADGE_LOWER["precision"]
          and (passive_lo or 0.0) >= BADGE_LOWER["passive"] and lo(s["semi"]) >= BADGE_LOWER["semi"])
    if ok:
        return ["USABLE WITH BADGE — lower bounds clear 90/90/90/95: parts lists may feed BOM/inventory with "
                "every line marked `extracted`."]
    return [f"INCONCLUSIVE — point estimates clear the stop line, but the lower bounds do not (only {n} "
            f"schematics). Extend toward the 60-schematic golden set."]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pilot", required=True, help="folder with <slug>.truth.csv sheets")
    ap.add_argument("--extractions", required=True)
    ap.add_argument("--csv", help="write the part-level diff here")
    args = ap.parse_args(argv)
    pilot, ext = Path(args.pilot), Path(args.extractions)
    rows = score_dir(pilot, ext)
    print(report(rows, pilot, ext))
    if args.csv and rows:
        cols = ["slug", "ref", "truth_type", "truth_value", "ext_type", "ext_value", "verdict"]
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerows(r["diff"])
        print(f"wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
