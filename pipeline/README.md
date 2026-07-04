<!-- SPDX-License-Identifier: MIT -->
# Pipeline — schematic → structured data

Offline batch tooling that turns a guitar-pedal **schematic image** into
structured data: a parts + nets JSON, an openable **KiCad** project, and rows
in a SQLite DB. This is **separate from the app** — the macOS app never runs
any of this. All vision/LLM work happens here, driven by Claude/Gemini
sessions.

## The data flow

```
schematic image ──(vision extraction)──▶ extractions/<slug>.json
                                              │
                    ┌─────────────────────────┼──────────────────────────┐
                    ▼                          ▼                          ▼
        netlist_to_kicad.py          build_database.py            package_dataset.py
        KiCad project (grid,          pedal_schematics.db          redistributable
        symbols, ngspice deck)        (schematics/components/       dataset export
                                       connections)
```

## State & the review-and-refine loop

`manifest.py` is the **single source of truth** for progress. Each pedal-subset
schematic is in one state:

| state | meaning |
|---|---|
| `pending` | no extraction yet |
| `review`  | extraction exists, **awaiting human review/refinement** |
| `done`    | human-reviewed and refined — the extraction is trusted |
| `skip`    | deliberately excluded |

```sh
python3 manifest.py status          # counts + progress
python3 manifest.py sync            # promote any pending-with-extraction → review (self-heals)
python3 manifest.py review 10       # list the next 10 awaiting review
python3 manifest.py mark <slug> done   # after you refine one
```

**Current state:** all 565 schematics extracted (Gemini Flash) and loaded into
`pedal_schematics.db`; `manifest.py sync` reconciled the manifest to
**review**. The next phase is reviewing each extraction to refine the DB.

## Extraction engines

Vision extraction reads `extraction_prompt.txt` (the canonical JSON schema every
engine must follow) and writes `extractions/<slug>.json`. Extraction is
token-heavy, so it can run on either quota:

- **Claude** (this session) — when limits allow.
- **Gemini** — the fallback when Claude limits are reached (Gemini scores best
  on circuit-schematic benchmarks). Coordinated via
  `../../../Claude/shared-with-gemini/SHARED_MEMORY.md`.

Re-extraction during refinement targets one slug at a time via `chunk_driver.py`.

## Modules

| file | role |
|---|---|
| `manifest.py` | progress state authority (`status`/`sync`/`review`/`next`/`mark`) |
| `extraction_prompt.txt` | the JSON schema contract every engine reads |
| `chunk_driver.py` | drive vision extraction over a chunk of schematics |
| `netlist_to_kicad.py` | extraction JSON → openable KiCad project + ngspice deck |
| `build_database.py` | extraction JSONs → `pedal_schematics.db` |
| `rank_pedals.py` | order the queue by pedal popularity |
| `query_topology.py` | topology / circuit queries over the DB |
| `package_dataset.py` | export a redistributable dataset (excludes copyrighted source) |
| `schema.sql` | SQLite schema |
| `tools/` | corpus + OCR helpers that feed the app's seeds (`generate_native_index.py`, `analyze_schematics.py`, `download_schematics.py`) |

## Local-only data (not in git)

`extractions/`, `pedal_schematics.db`, `kicad-projects/`, `manifest.json`, and
any schematic images are **derived from copyrighted schematics** and stay
user-local (see the root `.gitignore`). Only the code is published.

## Setup

```sh
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# OCR extras: brew install tesseract poppler kicad
```
