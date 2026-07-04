# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
manifest.py — track the schematic->KiCad pipeline progress and pick the next chunk.

The pedal-worthy subset (excludes reference books, bare synth modules, PSUs,
oscillators, MIDI, misc) is what we convert. State lives in
pipeline/manifest.json: each schematic is pending | done | review | skip.

State meaning (review-and-refine workflow):
  pending  no extraction yet
  review   extraction exists, awaiting human review/refinement of the DB
  done     human-reviewed and refined — the extraction is trusted
  skip     deliberately excluded

Commands:
  build            (re)build the manifest from the schematics index (keeps state)
  status           print counts + progress
  sync             reconcile with extractions on disk: pending -> review for any
                   schematic whose extraction JSON exists (never downgrades)
  next N            print the file paths of the next N pending schematics (for a chunk)
  review N         print the next N schematics awaiting review (state=review)
  mark <slug> <state>   set a schematic's state (e.g. mark <slug> done after refining)
"""
import json, sys, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX = Path.home() / "Library/Application Support/PedalWorkshop/schematics.json"
MANIFEST = HERE / "manifest.json"

# Effect types worth turning into KiCad pedal/effect projects, in the order
# we process them (classic guitar pedals first, utility/mods last).
# Excluded: reference, synth, oscillator, power, midi, misc, amplifier,
# envelope (the ADSR-generator folder is synth modules, not guitar pedals).
PRIORITY = ["distortion", "fuzz", "delay", "chorus", "phaser", "flanger",
            "tremolo", "filter", "compressor", "eq", "reverb", "ring_mod",
            "pitch", "utility", "modification"]
PEDAL_TYPES = set(PRIORITY)


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower() or "circuit"


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"entries": {}}


def save_manifest(m: dict) -> None:
    MANIFEST.write_text(json.dumps(m, indent=1))


def build() -> None:
    idx = json.loads(INDEX.read_text())
    m = load_manifest()
    e = m["entries"]
    added = 0
    for s in idx:
        if s["effect_type"] not in PEDAL_TYPES:
            continue
        key = s["file_path"]
        if key not in e:
            e[key] = {"name": Path(s["file_name"]).stem, "slug": slug(Path(s["file_name"]).stem),
                      "effect_type": s["effect_type"], "file_type": s["file_type"],
                      "prio": PRIORITY.index(s["effect_type"]), "state": "pending"}
            added += 1
        else:
            e[key]["prio"] = PRIORITY.index(s["effect_type"])  # keep prio current
    # Prune pending entries whose type is no longer in scope (never touch done/review).
    pruned = [k for k, v in e.items()
              if v["state"] == "pending" and v["effect_type"] not in PEDAL_TYPES]
    for k in pruned:
        del e[k]
    save_manifest(m)
    print(f"manifest: {len(e)} pedal-subset schematics ({added} added, {len(pruned)} pruned)")


def extraction_slugs() -> set:
    """Slugs whose extraction JSON exists on disk (extractions/<slug>.json)."""
    return {p.stem for p in (HERE / "extractions").glob("*.json")}


def status() -> None:
    e = load_manifest()["entries"]
    from collections import Counter
    c = Counter(v["state"] for v in e.values())
    total = len(e)
    done = c.get("done", 0)          # human-reviewed & refined
    review = c.get("review", 0)      # extracted, awaiting review
    print(f"total pedal-subset: {total}")
    for st in ("done", "review", "pending", "skip"):
        print(f"  {st:8s} {c.get(st, 0)}")
    if total:
        print(f"refined (done):   {done}/{total} = {100*done/total:.1f}%")
        print(f"awaiting review:  {review}")
    extracted = len(extraction_slugs())
    print(f"extractions on disk: {extracted}")


def sync() -> None:
    """Reconcile the manifest with extractions on disk.

    Any entry that is still 'pending' but has an extraction JSON on disk is
    promoted to 'review' (extracted, awaiting human refinement). Never
    downgrades an entry already at review/done/skip. This is the single
    self-healing bookkeeping pass — run it after any bulk extraction so the
    manifest reflects reality without re-running extraction.
    """
    m = load_manifest()
    e = m["entries"]
    have = extraction_slugs()
    promoted = 0
    for v in e.values():
        if v["slug"] in have and v["state"] == "pending":
            v["state"] = "review"
            promoted += 1
    save_manifest(m)
    orphans = have - {v["slug"] for v in e.values()}
    print(f"sync: {promoted} pending -> review "
          f"({len(have)} extractions on disk, {len(e)} manifest entries, "
          f"{len(orphans)} extraction(s) with no manifest entry)")


def review_chunk(n: int) -> None:
    """Print the next N schematics awaiting review, classic pedals first."""
    e = load_manifest()["entries"]
    items = [(v.get("prio", 99), v["name"].lower(), k) for k, v in e.items()
             if v["state"] == "review"]
    for _, _, k in sorted(items)[:n]:
        print(k)


def watch(interval: int = 30) -> None:
    """Redraw status every `interval` seconds until Ctrl-C."""
    import time
    try:
        while True:
            print("\033[2J\033[H", end="")  # clear screen, home cursor
            print(time.strftime("%H:%M:%S"), "— pedal schematic scan\n")
            status()
            time.sleep(interval)
    except KeyboardInterrupt:
        pass


def pending_sorted(e: dict) -> list[str]:
    """Pending file paths, classic pedals first (prio), then by name."""
    pend = [(v.get("prio", 99), v["name"].lower(), k) for k, v in e.items()
            if v["state"] == "pending"]
    return [k for _, _, k in sorted(pend)]


def next_chunk(n: int) -> None:
    e = load_manifest()["entries"]
    for p in pending_sorted(e)[:n]:
        print(p)


def mark(slug_or_path: str, state: str) -> None:
    m = load_manifest()
    e = m["entries"]
    for k, v in e.items():
        if k == slug_or_path or v["slug"] == slug_or_path:
            v["state"] = state
            save_manifest(m)
            print(f"marked {v['slug']} -> {state}")
            return
    print(f"not found: {slug_or_path}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "build": build()
    elif cmd == "status": status()
    elif cmd == "sync": sync()
    elif cmd == "watch": watch(int(sys.argv[2]) if len(sys.argv) > 2 else 30)
    elif cmd == "next": next_chunk(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    elif cmd == "review": review_chunk(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    elif cmd == "mark": mark(sys.argv[2], sys.argv[3])
    else: print(__doc__)
