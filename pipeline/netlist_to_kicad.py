# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
netlist_to_kicad.py — generate a KiCad project from a vision-extraction JSON.

Input (one file per schematic, produced by the Claude vision-extraction stage):
{
  "name": "Proco Rat 2",
  "source_image": "/abs/path/to/schematic.pdf",
  "effect_type": "distortion",
  "signal_path": "input buffer -> clipping opamp -> tone -> output",
  "parts": [
    {"ref": "R1", "type": "resistor", "value": "1M", "pins": 2},
    {"ref": "IC1", "type": "ic", "value": "LM308", "pins": 8},
    ...
  ],
  "nets": [
    {"name": "IN", "pins": ["J1.1", "R1.1"]},
    {"name": "N1", "pins": ["R1.2", "IC1.3"]},
    ...
  ],
  "notes": "...", "confidence": "high|medium|low", "issues": ["..."]
}

Output directory (never overwrites without --force):
  <out>/<slug>/
    <slug>.kicad_pro       project
    <slug>.kicad_sch       schematic: generated box symbols on a grid, every
                           pin carries a wire stub + global net label (an
                           electrically-complete "netlist schematic" — meant
                           for editing/verification, not wall art)
    sim/<slug>.cir         draft ngspice deck (R/C/L + known Q/opamp models;
                           unmodelable parts listed in the header)
    extraction.json        the input, for provenance
    report.json            sanity-check results

Sanity checks: pin-count consistency, duplicate refs, floating nets,
pins referenced but not declared. Failures downgrade status, never crash.

Usage: python3 netlist_to_kicad.py extraction.json -o /path/to/kicad-projects
"""
import argparse
import json
import re
import sys
import uuid
from pathlib import Path

GRID_COLS = 6
CELL_W, CELL_H = 60.96, 45.72   # mm; both exact multiples of the 1.27 grid
PIN_LEN = 3.81                  # 3 × 1.27
PIN_PITCH = 2.54                # 2 × 1.27
ORIGIN_X, ORIGIN_Y = 25.4, 25.4  # 20 × 1.27 — keeps every derived point on-grid
GRID = 1.27

def snap(v: float) -> float:
    """Round to KiCad's 1.27 mm schematic grid so wire endpoints connect cleanly."""
    return round(round(v / GRID) * GRID, 4)

# Known one-liner SPICE models (measured style: tens–hundreds of bytes each).
SPICE_MODELS = {
    "2N3904": ".model 2N3904 NPN(IS=1E-14 VAF=100 BF=300 IKF=0.4 XTB=1.5 BR=4 CJC=4E-12 CJE=8E-12 RB=20 RC=0.1 RE=0.1 TR=250E-9 TF=350E-12 ITF=1 VTF=2 XTF=3)",
    "2N3906": ".model 2N3906 PNP(IS=1E-14 VAF=100 BF=200 IKF=0.4 XTB=1.5 BR=4 CJC=4.5E-12 CJE=10E-12 RB=20 RC=0.1 RE=0.1)",
    "2N2222": ".model 2N2222 NPN(IS=1E-14 VAF=100 BF=200 IKF=0.3 XTB=1.5 BR=3 CJC=8E-12 CJE=25E-12 TR=100E-9 TF=400E-12 ITF=1 VTF=2 XTF=3 RB=10 RC=0.3 RE=0.2)",
    "2N5088": ".model 2N5088 NPN(IS=5.911E-15 BF=1122 VAF=90 IKF=0.04 XTB=1.5 CJC=4.017E-12 CJE=4.973E-12 RB=10)",
    "BC108":  ".model BC108 NPN(IS=1.8E-14 BF=400 VAF=80 IKF=0.1 CJC=5E-12 CJE=12E-12 RB=30)",
    "BC109":  ".model BC109 NPN(IS=1.8E-14 BF=520 VAF=80 IKF=0.1 CJC=5E-12 CJE=12E-12 RB=30)",
    "2N5457": ".model 2N5457 NJF(Beta=1.125m Vto=-1.372 Lambda=2.3m Is=33.57f Cgd=1.6p Cgs=2p)",
    "J201":   ".model J201 NJF(Beta=0.2m Vto=-0.67 Lambda=2m Is=33f Cgd=2.4p Cgs=2.4p)",
    "1N4148": ".model 1N4148 D(IS=4.352E-9 N=1.906 BV=110 IBV=0.0001 RS=0.6458 CJO=7.048E-13 VJ=0.869 M=0.03 FC=0.5 TT=3.48E-9)",
    "1N914":  ".model 1N914 D(IS=2.52E-9 N=1.752 RS=0.568 BV=110 IBV=1E-4 CJO=4E-12 TT=20E-9)",
    "1N34":   ".model 1N34 D(IS=2E-7 RS=7 N=1.3 CJO=1.5E-12 EG=0.67)",
}
UNMODELABLE = {"PT2399", "MN3007", "MN3005", "MN3101", "MN3102", "SAD1024",
               "TDA1022", "BL3208", "V3205", "RE-101", "CD4047"}

TWO_PIN = {"resistor", "capacitor", "inductor", "diode", "led", "zener",
           "battery", "fuse", "crystal", "photocell", "ldr", "lamp"}
DEFAULT_PINS = {"transistor": 3, "jfet": 3, "mosfet": 3, "potentiometer": 3,
                "switch": 3, "jack": 2, "opamp": 8, "ic": 8, "transformer": 4,
                "vactrol": 4}
REF_PREFIX = {"resistor": "R", "capacitor": "C", "inductor": "L", "diode": "D",
              "led": "D", "transistor": "Q", "jfet": "Q", "ic": "U", "opamp": "U",
              "potentiometer": "RV", "switch": "SW", "jack": "J"}


def slugify(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
    return s or "circuit"


def part_pins(p: dict) -> int:
    if isinstance(p.get("pins"), int) and p["pins"] > 0:
        return min(p["pins"], 40)
    t = p.get("type", "").lower()
    if t in TWO_PIN:
        return 2
    return DEFAULT_PINS.get(t, 2)


def sanity_check(data: dict) -> dict:
    """Mechanical checks on the extraction. Returns a report dict."""
    problems, warnings = [], []
    parts = {p["ref"]: p for p in data.get("parts", [])}
    if len(parts) != len(data.get("parts", [])):
        problems.append("duplicate reference designators")

    declared = {}          # ref -> pin count
    for ref, p in parts.items():
        declared[ref] = part_pins(p)

    used = {}              # ref -> set of pins used in nets
    for net in data.get("nets", []):
        if len(net.get("pins", [])) < 2:
            warnings.append(f"net '{net.get('name')}' has <2 pins (floating)")
        for pin in net.get("pins", []):
            m = re.match(r"^(.+?)\.(\d+)$", str(pin))
            if not m:
                problems.append(f"unparseable pin ref '{pin}'")
                continue
            ref, pn = m.group(1), int(m.group(2))
            if ref not in parts:
                problems.append(f"net pin '{pin}' references undeclared part")
                continue
            if pn < 1 or pn > declared[ref]:
                problems.append(f"pin {pin} out of range (has {declared[ref]} pins)")
            used.setdefault(ref, set()).add(pn)

    for ref, p in parts.items():
        t = p.get("type", "").lower()
        n_used = len(used.get(ref, set()))
        if t in TWO_PIN and n_used not in (0, 2):
            warnings.append(f"{ref} ({t}) has {n_used} connected pins, expected 2")
        if t in ("transistor", "jfet", "mosfet") and n_used not in (0, 3):
            warnings.append(f"{ref} ({t}) has {n_used} connected pins, expected 3")
        if n_used == 0:
            warnings.append(f"{ref} appears in no net")

    return {"problems": problems, "warnings": warnings,
            "part_count": len(parts), "net_count": len(data.get("nets", []))}


# ── KiCad s-expression emitters ──────────────────────────────────────────────

def esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def lib_symbol(name: str, npins: int, top_id: str | None = None) -> str:
    """Generic box symbol with pins split left/right, 2.54 pitch.
    top_id: full symbol id — "GEN:BOXn" when embedded in a schematic,
    "BOXn" when written into a standalone .kicad_sym library."""
    top = top_id or f"GEN:{name}"
    left = (npins + 1) // 2
    right = npins - left
    h = max(left, right) * PIN_PITCH + PIN_PITCH
    w = 15.24
    out = [f'    (symbol "{top}" (in_bom yes) (on_board yes)',
           f'      (property "Reference" "X" (at 0 {h/2 + 2.54:.2f} 0) (effects (font (size 1.27 1.27))))',
           f'      (property "Value" "{name}" (at 0 {-h/2 - 2.54:.2f} 0) (effects (font (size 1.27 1.27))))',
           f'      (symbol "{name}_0_1"',
           f'        (rectangle (start {-w/2:.2f} {h/2:.2f}) (end {w/2:.2f} {-h/2:.2f})'
           f' (stroke (width 0.254) (type default)) (fill (type background))))',
           f'      (symbol "{name}_1_1"']
    for i in range(left):
        y = h / 2 - PIN_PITCH - i * PIN_PITCH
        out.append(f'        (pin passive line (at {-w/2 - PIN_LEN:.2f} {y:.2f} 0) (length {PIN_LEN})'
                   f' (name "{i+1}" (effects (font (size 1.27 1.27))))'
                   f' (number "{i+1}" (effects (font (size 1.27 1.27)))))')
    for i in range(right):
        y = h / 2 - PIN_PITCH - i * PIN_PITCH
        out.append(f'        (pin passive line (at {w/2 + PIN_LEN:.2f} {y:.2f} 180) (length {PIN_LEN})'
                   f' (name "{left+i+1}" (effects (font (size 1.27 1.27))))'
                   f' (number "{left+i+1}" (effects (font (size 1.27 1.27)))))')
    out.append("      ))")
    return "\n".join(out)


def pin_positions(npins: int, cx: float, cy: float):
    """Absolute (x, y, side) for each pin of a placed box symbol.
    NOTE: schematic Y grows DOWN; symbol-local +Y (up) maps to sheet -Y."""
    left = (npins + 1) // 2
    w = 15.24
    pos = {}
    for i in range(left):
        y = cy - (max(left, npins - left) * PIN_PITCH + PIN_PITCH) / 2 + PIN_PITCH + i * PIN_PITCH
        pos[i + 1] = (snap(cx - w / 2 - PIN_LEN), snap(y), "L")
    for i in range(npins - left):
        y = cy - (max(left, npins - left) * PIN_PITCH + PIN_PITCH) / 2 + PIN_PITCH + i * PIN_PITCH
        pos[left + i + 1] = (snap(cx + w / 2 + PIN_LEN), snap(y), "R")
    return pos


def generate_sch(data: dict, sheet_uuid: str) -> str:
    parts = data.get("parts", [])
    # pin -> net name map
    pin_net = {}
    for net in data.get("nets", []):
        for pin in net.get("pins", []):
            pin_net[str(pin)] = net["name"]

    # unique lib symbols by pin count
    needed = sorted({part_pins(p) for p in parts})
    libs = "\n".join(lib_symbol(f"BOX{n}", n) for n in needed)

    body, labels = [], []
    for idx, p in enumerate(parts):
        npins = part_pins(p)
        col, row = idx % GRID_COLS, idx // GRID_COLS
        cx, cy = snap(ORIGIN_X + col * CELL_W), snap(ORIGIN_Y + row * CELL_H)
        u = uuid.uuid4()
        body.append(
            f'  (symbol (lib_id "GEN:BOX{npins}") (at {cx:.2f} {cy:.2f} 0) (unit 1)\n'
            f'    (in_bom yes) (on_board yes) (uuid "{u}")\n'
            f'    (property "Reference" "{esc(p["ref"])}" (at {cx:.2f} {cy - 14:.2f} 0)'
            f' (effects (font (size 1.27 1.27))))\n'
            f'    (property "Value" "{esc(p.get("value", "?"))}" (at {cx:.2f} {cy + 14:.2f} 0)'
            f' (effects (font (size 1.27 1.27))))\n'
            f'    (instances (project "{esc(data.get("name", "gen"))}"'
            f' (path "/{sheet_uuid}" (reference "{esc(p["ref"])}") (unit 1))))\n'
            f'  )'
        )
        for pn, (px, py, side) in pin_positions(npins, cx, cy).items():
            net = pin_net.get(f'{p["ref"]}.{pn}')
            if not net:
                continue
            stub = PIN_PITCH if side == "R" else -PIN_PITCH
            lx = snap(px + stub)
            body.append(
                f'  (wire (pts (xy {px:.2f} {py:.2f}) (xy {lx:.2f} {py:.2f}))'
                f' (stroke (width 0)) (uuid "{uuid.uuid4()}"))'
            )
            angle = 0 if side == "R" else 180
            labels.append(
                f'  (global_label "{esc(net)}" (shape passive) (at {lx:.2f} {py:.2f} {angle})'
                f' (effects (font (size 1.27 1.27)) (justify {"left" if side == "R" else "right"}))'
                f' (uuid "{uuid.uuid4()}"))'
            )

    title = esc(data.get("name", "Generated circuit"))
    src = esc(Path(data.get("source_image", "")).name)
    return (
        '(kicad_sch\n'
        '  (version 20251024)\n'
        '  (generator "pedal_workshop_pipeline")\n'
        f'  (uuid "{sheet_uuid}")\n'
        '  (paper "A3")\n'
        '  (title_block\n'
        f'    (title "{title}")\n'
        f'    (comment 1 "Generated from {src} — verify against the original before trusting")\n'
        f'    (comment 2 "Signal path: {esc(data.get("signal_path", ""))[:120]}")\n'
        '  )\n'
        '  (lib_symbols\n' + libs + '\n  )\n'
        + "\n".join(body) + "\n"
        + "\n".join(labels) + "\n"
        '  (sheet_instances (path "/" (page "1")))\n'
        '  (embedded_fonts no)\n'
        ')\n'
    )


def write_shared_lib(path: Path) -> None:
    """One GEN.kicad_sym at the projects root, shared by every project so ERC
    resolves the GEN: library and the box symbols are placeable when editing."""
    if path.exists():
        return
    syms = "\n".join(lib_symbol(f"BOX{n}", n, top_id=f"BOX{n}") for n in range(2, 21))
    path.write_text(
        '(kicad_symbol_lib (version 20251024) (generator "pedal_workshop_pipeline")\n'
        + syms + "\n)\n"
    )


def write_sym_lib_table(pdir: Path) -> None:
    (pdir / "sym-lib-table").write_text(
        '(sym_lib_table\n  (version 7)\n'
        '  (lib (name "GEN")(type "KiCad")(uri "${KIPRJMOD}/../GEN.kicad_sym")'
        '(options "")(descr "Generated generic box symbols"))\n)\n'
    )


def generate_pro(name: str) -> str:
    return json.dumps({
        "meta": {"filename": f"{name}.kicad_pro", "version": 3},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
    }, indent=2)


def generate_cir(data: dict) -> tuple[str, list[str]]:
    """Draft ngspice deck. Returns (deck, unmodelable_parts)."""
    lines = [f'* {data.get("name", "circuit")} — DRAFT deck generated from vision extraction',
             f'* Source: {data.get("source_image", "?")}',
             '* Verify topology before trusting any result.']
    unmodelable, models_used = [], set()
    netnum, netmap = 0, {"GND": "0", "0": "0"}

    def n(name):
        nonlocal netnum
        if name not in netmap:
            netnum += 1
            netmap[name] = f"n{netnum}"
        return netmap[name]

    pin_net = {}
    for net in data.get("nets", []):
        for pin in net.get("pins", []):
            pin_net[str(pin)] = net["name"]

    for p in data.get("parts", []):
        t, ref, val = p.get("type", "").lower(), p["ref"], p.get("value", "")
        pins = [pin_net.get(f"{ref}.{i+1}", f"nc_{ref}_{i+1}") for i in range(part_pins(p))]
        upval = val.upper().replace(" ", "")
        if t == "resistor" and len(pins) >= 2:
            lines.append(f"R{ref[1:] if ref[0]=='R' else ref} {n(pins[0])} {n(pins[1])} {val}")
        elif t == "capacitor" and len(pins) >= 2:
            lines.append(f"C{ref[1:] if ref[0]=='C' else ref} {n(pins[0])} {n(pins[1])} {val}")
        elif t in ("diode", "led", "zener") and len(pins) >= 2:
            model = next((m for m in SPICE_MODELS if m in upval), None)
            mname = model or "DGEN"
            lines.append(f"D{ref} {n(pins[0])} {n(pins[1])} {mname}")
            models_used.add(SPICE_MODELS.get(mname, ".model DGEN D(IS=1E-9)"))
        elif t in ("transistor", "jfet") and len(pins) >= 3:
            model = next((m for m in SPICE_MODELS if m in upval), None)
            if model:
                lines.append(f"Q{ref} {n(pins[0])} {n(pins[1])} {n(pins[2])} {model} ; pin order per extraction — VERIFY C/B/E")
                models_used.add(SPICE_MODELS[model])
            else:
                unmodelable.append(f"{ref} ({val})")
        elif upval in UNMODELABLE or (t in ("ic", "opamp") and upval in UNMODELABLE):
            unmodelable.append(f"{ref} ({val})")
        elif t in ("ic", "opamp"):
            unmodelable.append(f"{ref} ({val}) — no model in built-in set")
    lines += sorted(models_used)
    if unmodelable:
        lines.insert(3, "* UNMODELED PARTS: " + "; ".join(unmodelable))
    lines += [
        "* Uncomment + adapt to simulate (component deck alone is 'incomplete' to ngspice):",
        "* Vsupply n9V 0 DC 9",
        "* Vin nIN 0 DC 0 AC 1 SIN(0 0.1 1k)",
        "* .tran 10u 20m",
        "* .control",
        "* run",
        "* .endc",
    ]
    lines.append(".end")
    return "\n".join(lines) + "\n", unmodelable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("extraction", help="extraction JSON file")
    ap.add_argument("-o", "--out", required=True, help="output root for projects")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    data = json.loads(Path(args.extraction).read_text())
    slug = slugify(data.get("name", Path(args.extraction).stem))
    pdir = Path(args.out) / slug
    if pdir.exists() and not args.force:
        print(f"SKIP {slug}: exists (use --force)"); return
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "sim").mkdir(exist_ok=True)
    write_shared_lib(Path(args.out) / "GEN.kicad_sym")
    write_sym_lib_table(pdir)

    report = sanity_check(data)
    sheet_uuid = str(uuid.uuid4())
    (pdir / f"{slug}.kicad_sch").write_text(generate_sch(data, sheet_uuid))
    (pdir / f"{slug}.kicad_pro").write_text(generate_pro(slug))
    deck, unmod = generate_cir(data)
    (pdir / "sim" / f"{slug}.cir").write_text(deck)
    (pdir / "extraction.json").write_text(json.dumps(data, indent=1))
    report["unmodeled_parts"] = unmod
    report["status"] = ("needs-review" if report["problems"]
                        else "ok-with-warnings" if report["warnings"] else "ok")
    (pdir / "report.json").write_text(json.dumps(report, indent=1))
    print(f"OK {slug}: {report['part_count']} parts, {report['net_count']} nets, "
          f"status={report['status']}, unmodeled={len(unmod)}")


if __name__ == "__main__":
    main()
