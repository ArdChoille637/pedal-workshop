# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
chunk_driver.py — process a chunk of pending schematics into KiCad projects.

The token-heavy step is vision extraction (image -> parts+nets JSON). This can
run on different engines so work can be HANDED OFF when one hits its limits:

  --engine gemini   Local Gemini CLI (`gemini -p "@img ..."`) — uses GEMINI's
                    quota, not Claude's. Needs `gemini` CLI + live auth.
  --engine handoff  For the Gemini DESKTOP app: rasterize the next N pending
                    into handoff/images/ and write ONE paste-ready prompt
                    (handoff/PASTE_INTO_GEMINI.md). Drag the images into Gemini,
                    paste the prompt, save its reply to handoff/gemini_reply.txt.
  --engine ingest   Parse handoff/gemini_reply.txt (a JSON array or several
                    objects), match each to a pending schematic, build KiCad.
  --engine manual   One prompt+image bundle per schematic (per-item relay).
  --engine collect  (Re)generate KiCad from JSON already in extractions/.

Downstream is engine-independent: JSON -> netlist_to_kicad.py -> kicad-cli-clean
project -> manifest marked 'review'.

Usage:
  python3 chunk_driver.py --engine gemini --count 6
  python3 chunk_driver.py --engine manual --count 6
  python3 chunk_driver.py --engine collect
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTRACT_DIR = HERE / "extractions"
HANDOFF_DIR = HERE / "handoff"
PROMPT = (HERE / "extraction_prompt.txt").read_text()
OUT_ROOT = Path.home() / "Documents/schematics/kicad-projects"
REQUIRED_KEYS = {"name", "parts", "nets"}


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def manifest(*args):
    r = sh([sys.executable, str(HERE / "manifest.py"), *args])
    return r.stdout.strip()


def rasterize(path: Path) -> Path:
    """Return a PNG the vision model can read (png/jpeg/webp/heic only; convert
    PDF page 1 and GIF). Cached in a temp dir."""
    ext = path.suffix.lower()
    if ext in (".png", ".jpg", ".jpeg"):
        return path
    tmp = Path(tempfile.gettempdir()) / f"pw_{abs(hash(str(path)))}.png"
    if ext == ".pdf":
        sh(["pdftoppm", "-png", "-r", "200", "-f", "1", "-l", "1",
            str(path), str(tmp.with_suffix(""))])
        cand = tmp.with_suffix("").with_name(tmp.stem + "-1.png")
        return cand if cand.exists() else path
    # gif / bmp / tif -> png via macOS sips
    sh(["sips", "-s", "format", "png", str(path), "--out", str(tmp)])
    return tmp if tmp.exists() else path


def parse_json(text: str) -> dict | None:
    """Pull one JSON object out of model output (strip fences/prose)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < 0:
        return None
    try:
        d = json.loads(text[a:b + 1])
    except json.JSONDecodeError:
        return None
    return d if REQUIRED_KEYS <= set(d) else None


def parse_many(text: str) -> list[dict]:
    """Extract every extraction object from a batch reply (a JSON array, or
    several objects concatenated / fenced). Brace-matched, string-aware."""
    text = re.sub(r"```(?:json)?", "", text)
    try:                                   # whole thing is a JSON array?
        arr = json.loads(text[text.find("["):text.rfind("]") + 1])
        if isinstance(arr, list):
            good = [o for o in arr if isinstance(o, dict) and REQUIRED_KEYS <= set(o)]
            if good:
                return good
    except (json.JSONDecodeError, ValueError):
        pass
    out, depth, start, instr, esc = [], 0, None, False, False
    for i, ch in enumerate(text):          # scan for top-level {...} blocks
        if esc:
            esc = False; continue
        if ch == "\\" and instr:
            esc = True; continue
        if ch == '"':
            instr = not instr; continue
        if instr:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    o = json.loads(text[start:i + 1])
                    if isinstance(o, dict) and REQUIRED_KEYS <= set(o):
                        out.append(o)
                except json.JSONDecodeError:
                    pass
                start = None
    return out


def match_entry(obj: dict, entries: dict):
    """Tie a returned object back to a pending manifest entry by source-image
    basename, then by slug of the 'name' field."""
    from pathlib import PurePath
    src = PurePath(str(obj.get("source_image", ""))).name.lower()
    for path, v in entries.items():
        if v["state"] == "pending" and (PurePath(path).name.lower() == src or f"{v['slug']}.png" == src):
            return path, v
    want = slug(obj.get("name", ""))
    for path, v in entries.items():
        if v["state"] == "pending" and v["slug"] == want:
            return path, v
    return None, None


def extract_gemini(img: Path, source: str, effect: str) -> tuple[dict | None, str]:
    prompt = PROMPT.replace("<SOURCE_IMAGE>", source).replace("<EFFECT_TYPE>", effect)
    # @<abspath> loads the image into Gemini's multimodal context.
    r = sh(["gemini", "-o", "text", "--approval-mode", "plan",
            "-p", f"@{img} {prompt}"], timeout=360)
    if r.returncode == 130 or "Authentication cancelled" in r.stderr:
        return None, "AUTH_EXPIRED"
    d = parse_json(r.stdout)
    return (d, "ok" if d else "parse_fail:" + r.stdout[:80].replace("\n", " "))


def pending_chunk(n: int):
    """Next N pending, classic pedals first (matches manifest.pending_sorted)."""
    m = json.loads((HERE / "manifest.json").read_text())["entries"]
    pend = sorted(((v.get("prio", 99), v["name"].lower(), path, v)
                   for path, v in m.items() if v["state"] == "pending"))
    return [(path, v) for _, _, path, v in pend[:n]]


def generate(extraction_path: Path) -> str:
    r = sh([sys.executable, str(HERE / "netlist_to_kicad.py"),
            str(extraction_path), "-o", str(OUT_ROOT), "--force"])
    return r.stdout.strip() or r.stderr.strip()


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower() or "circuit"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine",
                    choices=["gemini", "handoff", "ingest", "manual", "collect"],
                    default="handoff")
    ap.add_argument("--count", type=int, default=8)
    args = ap.parse_args()
    EXTRACT_DIR.mkdir(exist_ok=True)

    if args.engine == "ingest":
        reply = HANDOFF_DIR / "gemini_reply.txt"
        if not reply.exists():
            print(f"paste Gemini's reply into {reply} first."); return
        entries = json.loads((HERE / "manifest.json").read_text())["entries"]
        objs = parse_many(reply.read_text())
        print(f"parsed {len(objs)} objects from the reply\n")
        matched = unmatched = 0
        for obj in objs:
            path, v = match_entry(obj, entries)
            if not v:
                print(f"  ?? no pending match for '{obj.get('name','?')}'"); unmatched += 1; continue
            obj["source_image"] = path
            obj.setdefault("effect_type", v["effect_type"])
            jf = EXTRACT_DIR / f"{v['slug']}.json"
            jf.write_text(json.dumps(obj, indent=1))
            print(f"  OK  {v['slug']}: {generate(jf)}")
            manifest("mark", v["slug"], "review"); matched += 1
        print(f"\ningested {matched} ({unmatched} unmatched). `manifest.py status` for totals.")
        return

    if args.engine == "collect":
        # Regenerate from any JSON already present for pending entries.
        done = 0
        m = json.loads((HERE / "manifest.json").read_text())["entries"]
        for path, v in list(m.items()):
            if v["state"] != "pending":
                continue
            jf = EXTRACT_DIR / f"{v['slug']}.json"
            if jf.exists():
                print(generate(jf)); manifest("mark", v["slug"], "review"); done += 1
        print(f"\ncollect: generated {done} from existing JSON"); return

    chunk = pending_chunk(args.count)
    if not chunk:
        print("nothing pending — all done or in review."); return
    print(f"chunk: {len(chunk)} schematics via {args.engine}\n")

    if args.engine == "handoff":
        imgdir = HANDOFF_DIR / "images"
        imgdir.mkdir(parents=True, exist_ok=True)
        for f in imgdir.glob("*"):
            f.unlink()
        names = []
        for path, v in chunk:
            png = rasterize(Path(path))
            dest = imgdir / f"{v['slug']}.png"
            dest.write_bytes(Path(png).read_bytes())
            names.append((v["slug"], v["effect_type"]))
        listing = "\n".join(f"  {i+1}. {s}.png  (effect_type: {et})"
                            for i, (s, et) in enumerate(names))
        batch = (
            f"I'm attaching {len(names)} guitar-pedal / audio-effect schematic images:\n{listing}\n\n"
            "For EACH attached image, extract it per these rules, then return a single JSON ARRAY "
            "with one object per image (same order). Set each object's \"source_image\" to the image's "
            "filename (e.g. \"proco-rat.png\") and \"effect_type\" to the one listed above.\n\n"
            "--- EXTRACTION RULES ---\n" + PROMPT +
            "\n--- OUTPUT: a JSON array of the above objects, and nothing else. ---\n"
        )
        (HANDOFF_DIR / "PASTE_INTO_GEMINI.md").write_text(batch)
        (HANDOFF_DIR / "gemini_reply.txt").write_text("")  # ready for the paste-back
        print(f"Prepared {len(names)} images in {imgdir}")
        print(f"1. Drag ALL images from that folder into the Gemini desktop app")
        print(f"2. Paste the text from {HANDOFF_DIR/'PASTE_INTO_GEMINI.md'}")
        print(f"3. Save Gemini's whole reply into {HANDOFF_DIR/'gemini_reply.txt'}")
        print(f"4. Run:  python3 {Path(__file__).name} --engine ingest")
        sh(["open", str(imgdir)]); sh(["open", str(HANDOFF_DIR / 'PASTE_INTO_GEMINI.md')])
        return

    if args.engine == "manual":
        HANDOFF_DIR.mkdir(exist_ok=True)
        for path, v in chunk:
            img = rasterize(Path(path))
            prompt = PROMPT.replace("<SOURCE_IMAGE>", path).replace("<EFFECT_TYPE>", v["effect_type"])
            bundle = HANDOFF_DIR / v["slug"]
            bundle.mkdir(exist_ok=True)
            (bundle / "prompt.txt").write_text(prompt)
            (bundle / "image_path.txt").write_text(str(img))
            print(f"  {v['slug']}: attach {img}\n     with handoff/{v['slug']}/prompt.txt")
        print(f"\nRelay each bundle to Gemini, save its JSON to extractions/<slug>.json,\n"
              f"then: python3 chunk_driver.py --engine collect")
        return

    ok = fail = 0
    for path, v in chunk:
        img = rasterize(Path(path))
        d, status = extract_gemini(img, path, v["effect_type"])
        if status == "AUTH_EXPIRED":
            print("\n!! Gemini auth expired. Run `gemini` once interactively to re-login\n"
                  "   (or export GEMINI_API_KEY), then re-run this command.")
            break
        if d:
            d.setdefault("source_image", path)
            d.setdefault("effect_type", v["effect_type"])
            jf = EXTRACT_DIR / f"{v['slug']}.json"
            jf.write_text(json.dumps(d, indent=1))
            print(f"  OK  {v['slug']}: {generate(jf)}")
            manifest("mark", v["slug"], "review"); ok += 1
        else:
            print(f"  FAIL {v['slug']}: {status}"); fail += 1
    print(f"\nchunk done: {ok} ok, {fail} failed. `python3 manifest.py status` for totals.")


if __name__ == "__main__":
    main()
