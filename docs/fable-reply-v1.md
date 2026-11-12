<!-- SPDX-License-Identifier: MIT -->
# Fable reply v1 — adversarial review + research-prompt factory

| | |
|---|---|
| **Answers** | `docs/handoff-fable-review-and-research.md` v1 |
| **Date** | 2026-11-11 |
| **Run in** | Claude Code (Fable 5.2) with the repo and the extraction data on disk — so the handoff's "measured facts" were re-measured, not taken on trust |
| **Companions (local-only, gitignored)** | `docs/research/census/census-batches.csv` (all 580 slugs → batch) and `docs/research/census/B01.csv … B29.csv` (one file per research chat) |

Epistemic labels used throughout: **VERIFIED** = I measured it or read the code today; **REPORTED** = secondary source; **UNVERIFIED** = from my memory or inference, no source opened this session. Nothing legal or about third-party tools below was web-checked — that is what the research prompts are for.

---

## 1. Assumptions & blocking questions

**Blocking questions: none.** Defaults I picked instead of asking:

1. **Ohio formation** is assumed. Only finding L6 (sales tax) and prompt B7 change if that is wrong.
2. **US-only sales at first.** EU/UK sale is treated as a later gate (it adds real obligations — see L3).
3. **The extraction DB does not feed the app today.** `CLAUDE.md` says the app does no schematic→project derivation, so every extraction problem below is a risk to *future* BOM import, not to current Build Analyzer results.

---

## 2. Task A — findings

### 2.1 What I re-measured (VERIFIED, 565 extraction JSONs, 2026-11-11)

| Measure | Value | What it means |
|---|---|---|
| Parts | 24,286 | matches the handoff |
| Nets | 4,889 | ≈ 8.7 per schematic |
| Schematics with **zero nets** | **89 of 565 (16%)** | parts list only, no connectivity at all |
| Parts that appear in **no net** | **14,871 of 24,286 (61%)** | most components are unconnected |
| Pins placed in a net ÷ pins the parts declare | 17,449 ÷ 64,378 (**27%**) | median schematic 31%; 306 schematics under 50%; only **103** at ≥ 95% |
| Net pins that point at a part that does not exist | 470 | dangling references |
| Duplicate reference designators | 27 | |
| Single-pin nets | 212 | a net with one pin connects nothing |
| Pins that sit in more than one net | 232 | implied shorts or mis-traces |
| Extractor's own confidence | high 218 · medium 299 · low 48 | uncalibrated — never compared to truth |
| `issues[]` entries | 2,710 (every file has at least one) | avg 4.8 per schematic |
| R/C values with **no unit** | 1,494 of 16,500 (9%) | e.g. `620`, `.022` |
| Capacitor values in old leading-dot form (`.022`, `.1uf`, `1uF 50v`, `.047 or .1uf`) or otherwise not a plain number+unit | 1,712 of 6,086 (28%) | counted with a strict parser; resistors: 327 |
| R/C values that are not E24 | 319 | legit odd values *or* misreads — a cheap review queue |
| Manifest rows vs unique slugs | 580 vs **564** | 16 slugs are used twice — see finding 5a |
| Zero-part schematics | 3 | two are DSP papers and one is a digital multi-effect — not extractable analog circuits |

Two handoff statements are wrong and should be corrected in v2:

- **"connections ≈ 22/schematic ⇒ netlist incomplete" — right conclusion, wrong evidence.** `build_database.py` stores each net as a *chain* (A→B, B→C), so a net of N pins always yields N−1 rows. The connection count says nothing about completeness. The pin-coverage numbers above are the real evidence, and they are worse than the hypothesis.
- **"`issues[]` lives only in the JSON" — partly wrong.** `build_database.py` joins them into `schematics.design_notes`. What the DB actually drops is `confidence`, `signal_path`, `effect_type`, each part's `pins` count, and net *names*.

### 2.2 Ranked findings (severity × cheapness of fix)

| # | Target | Claim attacked | Evidence / reasoning | Sev | Cheapest settling test | Fix |
|---|---|---|---|---|---|---|
| 1 | Extraction | "The DB can drive KiCad output" | 61% of parts unconnected, 89 files with no nets (VERIFIED) | **Blocker** | Already settled by the table above | Add a structural lint (pin coverage, dangling refs, dup refs, single-pin nets) to `manifest.py`; only the ~103 files at ≥ 95% coverage may produce KiCad projects; the rest are "parts-list only" until re-extracted |
| 2 | Extraction | "Parts lists are good enough for BOM/inventory demand" | Never measured against anything. Extractor confidence is self-reported | **Blocker** | 12-schematic pilot of the protocol in §2.4 (about 4–6 hours) | Run the pilot before any other extraction work |
| 3 | Analyzer | "`normalizeValue` makes equivalent values match" | It is string clean-up, not numeric (VERIFIED in `BuildAnalyzer.swift:158`): `100n` ≠ `0.1u` ≠ `.1uf` ≠ `100nF`; `10000` ≠ `10k`; `1meg` ≠ `1M`. Lower-casing also collapses `1M` (mega) and `1m` (milli) | **Major** | Unit test with 30 equivalent pairs — most will fail today | Numeric canonical value (C1 in §3). This is the single best fix per hour |
| 4 | Schema | "DB = extraction JSON" | DB drops confidence, pins, net names, signal path; chain-encodes nets (VERIFIED) | **Major** | Round-trip one JSON → DB → JSON and diff | Schema v2 in §2.3; treat JSON as the source of truth and the DB as a rebuildable index |
| 5 | Extraction | "Value strings are data" | Roles and guesses stored as values: `unknown`, `Not Specified`, `(Unlabeled)`, `POWER`, `*k`, `.047 or .1uf`, `10k LIN` (VERIFIED) | **Major** | Count non-parsing values per type (done: 28% of caps, 3% of resistors) | Canonicaliser emits `value_raw` + parsed fields + `parse_status`; unknowns become an explicit null, never a string |
| 5a | Manifest | "580 entries = 580 schematics" | The manifest has 580 rows but only **564 unique slugs** — 16 slugs occur twice (different source files, sometimes different categories). `extractions/<slug>.json` is keyed by slug, so one file of each pair may have overwritten the other or never been extracted (VERIFIED) | **Major** | For each of the 16 pairs, compare `source_image` in the JSON with both manifest rows | Make the key `slug` + short hash of the source path; re-extract the losing file of each pair |
| 6 | Analyzer | "Ready to build" is a safe verdict | `StockKey` is category + value only (VERIFIED). So a 100 n film and a 100 n MLCC match; a 16 V and a 50 V electrolytic match; pot taper and shaft are invisible unless typed into the value; any optional row is skipped; no enclosure/hardware check | **Major** | Build one real pedal from a "Ready" verdict and log every part that had to be swapped | Add optional `rating`, `dielectric`, `taper`, `package` attributes; match on them only when the BOM line sets them; show "Ready — n lines unverified" (C3) |
| 7 | Extraction | "Review all 565" is the plan | 565 × ~43 parts ≈ 24k judgments ≈ 200+ hours solo. Also ~70 entries (utility + modification) are mostly wiring diagrams and mods, not pedals | **Major** | Triage pass D0 (one chat, names only) | Review only what you intend to build; sample the rest (§2.4) |
| 8 | Clients/Jobs | "A second customer system is fine" | Two systems of record for one person means double entry and drift. But ERPNext is not deployed yet, and the Workshop feature is built | **Major** | Count: how many clients/jobs per month? Under ~10 → local is fine | Keep Workshop-local **now**; make ERPNext the system of record for customers/invoices **when it is live**; Workshop then holds only `jobId ↔ projectId` + bench notes. Exit path: CSV export shaped like ERPNext's Customer / Quotation import (C8) |
| 9 | Clients/Jobs | "PII is safe in local JSON" | `clients.json` sits in Application Support unencrypted (fine with FileVault on — UNVERIFIED that it is on). Risk is a support bundle, screenshot, or test fixture reaching the public repo | **Major** | `git log -p -S"@"` over the repo for e-mail addresses; confirm FileVault | Pre-commit `gitleaks` + a PII regex hook; fixtures use obviously fake data; Time Machine/restic backup includes Application Support |
| 10 | Stack | "~$10 VPS runs the stack" | ERPNext + MariaDB + Redis + workers, InvenTree + Postgres, Penpot (its own Postgres + Redis + exporter), n8n on 8 GB is tight (UNVERIFIED sizing) and it is one disk, one provider, one admin | **Major** | `docker stats` after a week of real use | Stage it: ERPNext first, add services only when a workflow needs them. Penpot and Obsidian do not need the server at all |
| 11 | Stack | "Backups exist" | No tested restore is recorded anywhere in the handoff | **Major** | Restore last night's backup to a throwaway VPS and log in | Prompt B3; make the restore drill a calendar item |
| 12 | Stack | "ERPNext fits a one-person US LLC" | Conspicuously missing from the plan: US bookkeeping fit (Schedule C or 1120-S mapping, 1099-NEC, sales-tax filing, bank feeds) and who does the tax return. ERPNext may be over-built against plain-text or simple ledgers (UNVERIFIED) | **Major** | Ask the tax preparer what export they want | Prompt B13 before investing more in ERPNext accounting |
| 13 | Process | "One extraction engine is enough" | All 565 came from one model (Gemini Flash) in one pass. No second reader, so no disagreement signal | **Major** | Re-extract 12 pilot schematics with a second model and diff | Two-reader ensemble: agreement → lower review priority, disagreement → review queue |
| 14 | Process | "Pipeline is reproducible" | Model version, prompt hash, date, and image hash are not stored per extraction (VERIFIED: JSON keys are name/source_image/effect_type/signal_path/parts/nets/confidence/issues only) | Minor | Check for a provenance block in any JSON — none | Add `provenance{engine, model, prompt_sha, image_sha256, extracted_at}` on every re-extraction |
| 15 | Schema | "ICs are captured" | `324` stored for an LM324; multi-unit op-amps appear as one `opamp` with no unit/pin mapping; power pins unknown | Minor | Grep for all-digit values on `opamp`/`ic` types | Part-number canonicaliser with an alias table (C2) |
| 16 | Stack | Tailscale as the only door | If the coordination service or your identity provider login fails you are locked out (UNVERIFIED how you log in) | Minor | Try to reach the VPS with Tailscale stopped | Keep one break-glass path: provider console + an SSH key stored offline |
| 17 | Process | Bus factor of one | No "if I am unavailable" document: where things run, how to export, who to call | Minor | — | One page in the vault; prompt B9 covers it |
| 18 | Legal | See §2.5 | | | | |

### 2.3 Schema v2 (keeps everything the extractors wrote)

Principle: **JSON files are the source of truth; the SQLite DB is a disposable index rebuilt from them.** Migration is additive — nothing is deleted from existing files.

```
extraction v2 (per slug)
  schema_version: 2
  provenance:  { engine, model, prompt_sha, image_sha256, extracted_at }
  review:      { state: extracted|human-checked|source-confirmed, by, date, golden: bool }
  confidence, signal_path, effect_type, issues[]        ← unchanged, kept verbatim
  parts[]:
    ref, type, pins                                     ← unchanged
    value_raw                                           ← today's "value", untouched
    value: { num, unit, parse_status: ok|ambiguous|unknown|not-a-value }
    part_number, tolerance, rating, dielectric, taper, package   ← all optional, null if not printed
    role            (e.g. POWER, INPUT — moves role words out of "value")
    line_status: extracted|human-checked|source-confirmed
    sources[]:      { tier: A|B|C, url, retrieved_on }   ← filled by the Task D census
  nets[]: { name, pins[] }                              ← unchanged
  lint:  { pin_coverage, dangling_refs, dup_refs, single_pin_nets, off_e24[] }
```

DB changes: add `net_pins(schematic_id, net_name, ref, pin)` (replaces the chain-encoded `connections`), add the new part columns, add `issues(schematic_id, text)` as rows instead of one joined string, add `lint` columns on `schematics`. Migration script: read v1 JSON → run the canonicaliser → write v2 beside it → rebuild DB → assert part count and `issues[]` are byte-identical to v1.

### 2.4 Sampling + golden-set protocol

**Two different questions — keep them apart:**
- *Fidelity:* did the extractor read **the image we have** correctly? Ground truth = a human reading that same image.
- *Correctness:* is the image itself the right circuit? Ground truth = a tier A/B BOM from the Task D census, for the same revision.

The golden set measures fidelity. The census measures correctness. A part can be extracted perfectly from a wrong drawing.

**Design**

| Step | What | Size | Effort |
|---|---|---|---|
| 0 | Structural lint on all 565 (automatic) | 565 | S — the script exists from this session |
| 1 | **Pilot** | 12 schematics | 4–6 h |
| 2 | **Full golden set** (includes the pilot) | 60 schematics ≈ 2,600 parts | ~25 h total |
| 3 | Freeze as regression fixtures | 60 | S |

**Stratification for the 60** (pick at random inside each cell, fixed seed, from the manifest):
- by `effect_type`, proportional, minimum 2 per type that has ≥ 15 entries;
- by `file_type`: gif 30 · pdf 16 · jpg 12 · png 2 (matches the corpus mix of 298/157/109/16);
- by extractor confidence: 20 high · 28 medium · 12 low (low is over-sampled on purpose — it tests whether the confidence field means anything);
- exclude the D0-triaged "not a circuit" entries.

**Truth-making:** read the image yourself into a spreadsheet (ref, type, value) *without* looking at the extraction, then diff by script. For nets, check only the schematics that pass lint at ≥ 95% pin coverage — the others fail by construction.

**Metrics** (report each with a 95% interval, bootstrapped over schematics, because errors cluster per drawing):
- BOM line **recall** (truth parts found) and **precision** (extracted parts that exist);
- **value accuracy** after canonicalisation, split: resistors · capacitors · semiconductors/ICs (part-number identity) · pots (value and taper separately);
- **net F1** over pin-pairs that share a net (only on lint-passing files);
- **calibration:** accuracy inside high / medium / low confidence.

**Thresholds**

| Decision | Rule |
|---|---|
| **Stop** after pilot | value accuracy < 90% or line recall < 90% → do not review further; re-extract with a second engine first (finding 13) |
| **Ship parts lists** for BOM/inventory use | lower 95% bound: recall ≥ 97%, precision ≥ 98%, passive value accuracy ≥ 97%, semiconductor identity ≥ 99% |
| **Ship with badge** | point estimates meet those numbers but the lower bound does not → usable only with every line marked `extracted` in the UI |
| **Ship nets / KiCad** | lint pin coverage ≥ 95% **and** golden net F1 ≥ 0.95. Today at most 103 files can even be candidates |
| **Regression gate** | CI fails if any golden metric drops more than 1 point after a prompt/engine change |

With 60 schematics and ~2,600 parts, a 95%-accurate extractor is measured to roughly ±2 points after the clustering penalty. That is enough to make the ship/stop call; it is not enough to certify any individual un-reviewed schematic — which is why line-level status in the UI matters more than a corpus-wide number.

### 2.5 Legal / regulatory exposure (all UNVERIFIED — from memory, not checked today)

| # | Topic | My understanding | Lawyer or form? |
|---|---|---|---|
| L1 | Cloning circuits | A circuit's function is generally not protected by copyright; the *drawing* of a schematic and PCB artwork can be. Patents on classic pedal circuits have mostly expired. The live risks are **trademarks** (product names, logos) and **trade dress** (enclosure look). Never sell under the original name; "inspired by" wording is itself a trademark question | **Lawyer**, one hour, before the first sale of a clone |
| L2 | FCC Part 15 | A purely analog pedal with no clock above 9 kHz is not a "digital device". Pedals with digital delay chips, charge pumps, microcontrollers or BBD clocks may be unintentional radiators needing Supplier's Declaration of Conformity and labelling, with some exemptions | **Form + test**, per product. Research prompt B7 must pin the exact sections |
| L3 | EU/UK | CE needs EMC conformity, RoHS, a technical file and Declaration of Conformity; WEEE needs per-country producer registration; the EU General Product Safety Regulation requires an EU-based responsible person. UKCA is separate | **Do not sell to EU/UK** until B7 is answered; then forms + a paid representative |
| L4 | Batteries | Pedals shipped without batteries avoid lithium shipping rules. Shipping with a 9 V alkaline is minor; anything lithium is regulated | Form (carrier rules) |
| L5 | Product liability | Mains-adjacent products and repairs of customers' gear create liability the LLC alone does not cover. General liability + products/completed-operations cover; a signed repair intake form with a liability limit | **Insurance broker** + lawyer-reviewed one-page form |
| L6 | Ohio sales tax | A vendor's licence is needed for retail sales; pedal sales are taxable; repair labour on tangible goods is likely taxable; marketplaces (Reverb, Etsy) collect for you on their sales; other states apply once you cross their economic-nexus thresholds | **Form** (Ohio Business Gateway); accountant for the repair-labour question |
| L7 | Corpus copyright | The schematic images are third-party works. Extracted *facts* (values, connectivity) are much safer than images, but a bulk structured dataset derived from one archive is still a risk to publish | Keep the dataset local (already the rule). Lawyer only if you ever want to publish it |

### 2.6 What looks over-built, and what is missing

- **Over-built for a no-employee LLC (UNVERIFIED opinion):** ERPNext manufacturing/HR modules; Penpot on a server; a full identity provider (SSO for one user); Metabase/Superset before there is data.
- **Missing:** tested restore; bookkeeping-to-tax-return path; a password manager decision; uptime alerting; an "if I am unavailable" page; a pre-commit PII/secret scan on the public repo; a decision on where customers live (finding 8).

---

## 3. Task C — roadmap

### 3.1 Prioritised 10

| # | Kind | Problem → change | Lives in | Measured by | Cost | Reuse (open source) |
|---|---|---|---|---|---|---|
| C1 | Accuracy | Values match as strings → **numeric canonical value** (`num` + `unit`), one shared table of test vectors used by both Swift and Python | app + pipeline | equivalent-pair test suite: 0 failures; share of corpus values with `parse_status: ok` | S | KiCad's value conventions; Python `quantiphy` (GPL — pipeline only, check) or 60 lines of own code |
| C2 | Accuracy | Substitutes invisible → **equivalence table** as static JSON: part-number aliases (`324`→`LM324`), drop-in groups, E-series neighbours | data + app | false "missing" verdicts on a test set of real builds | M | Prompt B14 finds open cross-reference data |
| C3 | Accuracy | "Ready" hides uncertainty → **line status** (`extracted` / `human-checked` / `source-confirmed`) on every BOM line; verdict reads "Ready — 3 lines unverified" | app + data | every imported line carries a status; none default to confirmed | S | — |
| C4 | Accuracy | No quality gate → **structural lint + golden-set regression** in the pipeline | pipeline | lint score per schematic; CI fails on regression | S (lint) + M (golden) | `pytest` |
| C5 | Accuracy | Lossy DB → **schema v2 migration** (§2.3) | pipeline + data | round-trip diff = 0; `issues[]` preserved | M | `jsonschema`, SQLite |
| C6 | Power | No bridge from corpus to app → **confirmed-BOM static JSON per project**, produced offline from census + extraction, imported by the app | pipeline → app | time from "pick a pedal" to an analysable BOM | M | KiCad BOM CSV as the interchange format |
| C7 | Power | "Which pedals use a J113?" → **parts search** over a static index built by `query_topology.py` | pipeline → app | query returns in < 100 ms on 24k parts | S | SQLite FTS5 or a prebuilt JSON index |
| C8 | Power | Lock-in → **import/export**: CSV, KiCad BOM, InvenTree part/stock CSV, ERPNext-shaped client/job CSV | app | round-trip an inventory through CSV with no loss | M | InvenTree import templates |
| C9 | Power | Shopping is manual → **shopping list grouped by supplier** with price roll-up from Mouser data, then cost + margin on a Job | app | list total vs a hand-priced build | M | KiCost concepts (pipeline-side only) |
| C10 | Robustness | Public repo, private data → **pre-commit `gitleaks` + PII/corpus-title scan**, and a packaging check that the bundle ships empty seeds | repo | hook blocks a planted e-mail address and a planted slug | S | `gitleaks` (MIT), `pre-commit` (MIT) |

Deliberately left off the top 10: enclosure/drill data, label/QR printing, serials/build history, "what can I build from stock" (it falls out of C6 + C1 almost for free once BOMs exist). All are worth doing after trust in the numbers is established.

### 3.2 Top three trust wins per hour

1. **C1 numeric values** — one small function plus tests removes the largest class of wrong answers the Analyzer can give today.
2. **C4 lint** — already prototyped in this session; it turns "574 awaiting review" into a ranked queue and tells you which 103 netlists are even candidates.
3. **C3 line status** — costs a field and a label, and makes every later number honest about where it came from.

---

## 4. Task B — research prompts (paste-ready)

Each block below is complete on its own. Paste one block into one research chat. Tool names in "Candidates" are **hypotheses** — several carry a suspicion I could not check today, flagged inside the prompt.

### B1 — Quote → invoice → payment for a one-person shop

```text
TITLE: Quote-to-cash for a one-person shop — ERPNext modules vs lighter open-source tools

WHY IT MATTERS
A one-owner US LLC (no employees) does media post-production, acoustic consulting, and builds/repairs guitar pedals. It needs quotes, deposits, invoices and signed approvals without running two customer databases.

OBJECTIVE
Recommend the smallest open-source setup that takes a job from quote → signed acceptance → deposit → invoice → paid, for under ~30 documents a month, and say whether ERPNext alone already covers it.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).

QUESTIONS (answer each; each must be checkable)
1. Can stock ERPNext (v15 or current) produce Quotation → Sales Order → deposit (advance payment) → Sales Invoice with no custom code? Cite the docs page for each step.
2. Which candidates support customer-facing quote acceptance (click-to-accept or e-signature) natively?
3. Which candidates' licences are OSI-approved today? (Suspicions to verify: Invoice Ninja uses the Elastic License; Akaunting moved to BSL; Crater development has stalled.)
4. Which open-source e-signature tool (Documenso, OpenSign, DocuSeal, others) can be self-hosted in under 1 GB RAM, and what is paid-only in each?
5. Are e-signatures from a self-hosted tool valid under the US ESIGN Act / UETA for a simple service quote? Cite a primary or bar-association source.
6. What does each candidate export (CSV, JSON, SQL dump, UBL/PDF) if the owner leaves?
7. Which candidates have a maintained n8n node or a documented REST API?
8. What is the real weekly admin time for a solo user, per user reports from the last 24 months?

CANDIDATES (starting hypotheses — verify each, then find at least 3 more)
ERPNext Selling + Accounts; Dolibarr; Invoice Ninja; Akaunting; Crater / InvoiceShelf; EspoCRM; Kimai (invoicing side); Documenso; OpenSign; DocuSeal.

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.

STOP CONDITION
Stop when every candidate row is filled or marked UNVERIFIED, and you can name one recommendation plus one fallback. Do not exceed 40 sources.
```

### B2 — Parts, BOM and supplier data: InvenTree ⇄ Pedal Workshop

```text
TITLE: Parts/BOM management and supplier-data access for a small electronics bench

WHY IT MATTERS
The owner runs a native macOS app ("Pedal Workshop", MIT, static JSON, no network AI) for bench inventory and build analysis, and plans InvenTree as the server-side parts system. Two inventories that drift apart are worse than one.

OBJECTIVE
Decide which system should own parts and stock, define the simplest file-based bridge between them, and list which supplier APIs may legally be used for prices.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).
Additional constraint: the macOS app must stay offline-capable and read/write plain files; any bridge is an export/import or an offline script, never a live dependency.

QUESTIONS
1. What import and export formats does InvenTree support for parts, stock and BOMs (CSV/JSON/API)? Cite the docs.
2. Does InvenTree have a maintained KiCad integration (plugin or library), and who maintains it?
3. Part-DB vs InvenTree vs PartKeepr: licence, last release, and is each still maintained? (Suspicion: PartKeepr is abandoned.)
4. Which distributor APIs permit programmatic price/stock lookup for a small business, and under what terms? Check Mouser, DigiKey, LCSC, TME, Farnell/Newark. Quote the relevant terms-of-use clause and rate limits.
5. Is there an open, redistributable parts/price dataset or aggregator? (Check Octopart/Nexar free tier terms, Kitspace's partinfo, others.)
6. Which open tools compute BOM cost roll-ups from a KiCad BOM (KiCost, KiBot, others), and which distributor back-ends still work?
7. Do Tayda Electronics, Love My Switches or Mammoth Electronics publish any official API or feed? If not, say so plainly.
8. What is the smallest stable identifier scheme to key a part across both systems (MPN, internal part number, both)?

CANDIDATES
InvenTree; Part-DB; PartKeepr; Kitspace; KiBot; KiCost; Ki-nTree; Binner; Nexar/Octopart API; Mouser API; DigiKey API; LCSC.

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".
Also deliver: a one-page field mapping (app inventory JSON ↔ InvenTree part/stock columns) expressed as a table.

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.

STOP CONDITION
Stop when the ownership question (which system is the source of truth for stock) has a one-sentence answer backed by the table.
```

### B3 — Backups and a tested-restore runbook

```text
TITLE: Backup, offsite copy and tested restore for a single self-hosted VPS

WHY IT MATTERS
A solo owner will run business records (ERPNext on MariaDB, InvenTree on PostgreSQL, n8n) on one small VPS. A backup that has never been restored is a hope, not a backup.

OBJECTIVE
Produce a concrete backup design and a restore drill the owner can run in under one hour, four times a year.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).

QUESTIONS
1. restic vs BorgBackup vs Kopia: licence, last release, encryption model, and behaviour when a repository is damaged.
2. What is the documented, consistent way to back up ERPNext (bench backup incl. files) and InvenTree (database + media)? Cite each project's docs.
3. For MariaDB and PostgreSQL in Docker, which method gives a consistent dump without downtime (mariadb-dump --single-transaction, pg_dump, snapshots)?
4. Offsite targets: Backblaze B2, Hetzner Storage Box, rsync.net, a home NAS over a mesh VPN — current price per 100 GB, egress cost, and whether append-only / object-lock is available.
5. How is ransomware-resistant (append-only) backup configured for the recommended tool + target?
6. What should the restore drill verify (login works, latest invoice present, file attachments open)? Give it as a checklist.
7. How does the owner get alerted when a backup did not run (dead-man's-switch pattern) without a paid SaaS? Check Healthchecks (self-hosted) and others.
8. What must be backed up from the owner's Mac as well (application data folders, password vault, Obsidian vault)?

CANDIDATES
restic; BorgBackup + Borgmatic; Kopia; Duplicati; rclone; Healthchecks; Backblaze B2; Hetzner Storage Box; rsync.net.

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".
Also deliver: the restore runbook as numbered steps with exact commands, marked clearly where a command was not tested by you.

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.

STOP CONDITION
Stop when the runbook covers: nightly backup, offsite copy, missed-backup alert, and a full restore to a fresh VPS.
```

### B4 — Identity, secrets and the private network

```text
TITLE: Passwords, login and private networking for one person running several self-hosted services

WHY IT MATTERS
One owner, no staff, several self-hosted web apps reached over Tailscale. The realistic threats are a lost laptop, a phished password and locking oneself out — not an insider.

OBJECTIVE
Recommend the least-effort setup that is safe for one user, and say plainly which enterprise-style components are unnecessary at this size.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).

QUESTIONS
1. Is a single-sign-on provider (Authentik, Keycloak, Authelia, Kanidm) worth running for one user, or do a password manager + per-app 2FA give equal protection with less to maintain? Argue both sides with sources.
2. Vaultwarden: licence, relationship to Bitwarden, audit history, and backup/restore procedure. Compare with KeePassXC + file sync.
3. Tailscale vs Headscale vs NetBird vs plain WireGuard: what is closed-source in each, what is the lock-out risk, and what does self-hosting the control plane cost in upkeep?
4. What is Tailscale's current free-plan limit and what happened to pricing/terms in the last 24 months?
5. How should break-glass access work if the mesh VPN or the identity provider is down (provider console, offline SSH key, recovery codes)?
6. Are hardware security keys (FIDO2) supported for login to each candidate and to the VPS provider?
7. Is an SSH certificate authority worthwhile for one admin and two machines, or is it over-engineering?
8. Where should API keys used by n8n workflows live, and how are they rotated?

CANDIDATES
Vaultwarden; KeePassXC; Bitwarden (self-hosted); Authentik; Keycloak; Authelia; Kanidm; Tailscale; Headscale; NetBird; WireGuard; step-ca.

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.

STOP CONDITION
Stop when you can state, in five lines, the setup for one user and the break-glass procedure.
```

### B5 — Monitoring and alerts to a phone

```text
TITLE: Minimal monitoring and phone alerting for one VPS, without a paid SaaS

WHY IT MATTERS
A solo owner cannot watch dashboards. The need is: be told when something important is down or a disk is filling, and otherwise hear nothing.

OBJECTIVE
Recommend the smallest monitoring setup that sends a phone alert for five conditions: service down, disk > 85%, backup missed, certificate expiring, n8n workflow failed.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).

QUESTIONS
1. Uptime Kuma, Gatus, Netdata, Beszel, Prometheus + Grafana + Alertmanager: licence, RAM use at idle, last release.
2. Which tool can watch itself — i.e. what alerts when the monitoring host is the one that died? (External heartbeat options, free and open.)
3. Open push-notification paths to iOS: ntfy (self-hosted and hosted), Gotify, Matrix, plain e-mail/SMS gateways. Which work reliably on iOS and why?
4. Has Netdata changed its licence or moved features to a paid cloud tier? Cite the change.
5. How are logs kept small and safe on one disk (journald limits, logrotate, Docker log options)?
6. How does n8n report a failed workflow (error workflow, webhook) and how is that wired to the alert path?
7. What is the false-alarm rate reported by users of the recommended tool, and how is alert fatigue avoided?
8. What is the total extra RAM and weekly upkeep of the recommended setup?

CANDIDATES
Uptime Kuma; Gatus; Beszel; Netdata; Prometheus/Grafana/Alertmanager; Healthchecks; ntfy; Gotify.

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.

STOP CONDITION
Stop when all five alert conditions map to a named tool and a named notification path.
```

### B6 — Selling physical pedals online

```text
TITLE: Storefront, payments, sales tax, shipping labels and repair returns for a very small US maker

WHY IT MATTERS
A one-person Ohio LLC (formation state to be confirmed) will sell small batches of guitar pedals and take in repairs. Volume will be tens of orders a month at most.

OBJECTIVE
Decide between a self-hosted open-source storefront, selling only on marketplaces, or a hosted shop — judged on total owner time, fees, and compliance burden.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).
Note: for payments, a closed processor (Stripe, PayPal, Square) is an acceptable named fallback because card networks are closed by nature. State that reasoning explicitly rather than forcing an open option that does not fit.

QUESTIONS
1. Medusa, Saleor, Vendure, WooCommerce, PrestaShop, Shopware: licence, self-host RAM, and what is paid-only.
2. At under 50 orders a month, what are the all-in fees for: own shop + Stripe, Reverb, Etsy, Shopify Basic? Show the arithmetic for a $180 pedal.
3. BTCPay Server: what does it actually solve for this seller, and what tax/accounting work does accepting crypto add in the US? Be candid if it is a poor fit.
4. Ohio sales tax for a small remote/online seller: registration, sourcing rule, filing frequency. Cite the Ohio Department of Taxation.
5. Marketplace-facilitator rules: on which platforms is tax collected for the seller, and what must the seller still file?
6. Economic-nexus thresholds in other US states: where is the current authoritative table?
7. Shipping labels: which open-source or free tools buy USPS/UPS labels (Shippo, EasyPost, Pirate Ship, carrier APIs), and what are their terms? Is any truly open-source option viable?
8. Returns/RMA for repairs: which candidates model "customer sends item in, item goes back" without custom code?

CANDIDATES
Medusa; Saleor; Vendure; WooCommerce; ERPNext Webshop; Reverb; Etsy; Shopify (fallback); BTCPay Server; Stripe (fallback); Pirate Ship; Shippo; EasyPost.

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".
Also deliver: a fee comparison table for a $180 sale and a $60 repair.

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.
Tax and legal statements must cite a government source and be labelled "needs accountant" or "needs lawyer" where applicable.

STOP CONDITION
Stop when you can recommend one selling channel for the first 12 months and name the trigger for revisiting it.
```

### B7 — Compliance register for selling pedals

```text
TITLE: Regulatory and legal checklist for a US one-person maker of guitar effect pedals

WHY IT MATTERS
The owner will sell and repair low-voltage (9–18 V DC) guitar pedals, some based on classic commercial circuits, some with digital chips. Getting this wrong risks fines, seized shipments or a trademark claim.

OBJECTIVE
Build a per-topic register stating: what the rule is, whether it applies, what the owner must do, and whether that is a FORM the owner can file or a question for a LAWYER / ACCOUNTANT / INSURANCE BROKER.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).
This prompt is legal research, not tool selection: where the scorecard asks for licence/release fields, replace them with: jurisdiction, governing text (section number), regulator, last amended, penalty.

QUESTIONS
1. FCC 47 CFR Part 15: which pedals are "digital devices" (clock above 9 kHz)? Which exemptions in §15.103 could apply? What do Supplier's Declaration of Conformity and labelling require? Quote the sections.
2. Do pedals containing PT2399, bucket-brigade clocks, charge pumps or microcontrollers fall under Part 15 Subpart B? Find FCC guidance (KDB) or state that none exists.
3. EU: what do the EMC Directive, RoHS, WEEE and the General Product Safety Regulation (EU 2023/988) require of a non-EU micro-seller shipping direct to consumers? Is an EU responsible person mandatory?
4. UK: UKCA vs CE acceptance status as of today, and UK WEEE/producer rules for small sellers.
5. US trademark and trade dress: what do courts and the USPTO say about selling a functional clone under a different name, and about "based on / inspired by" wording? Cite cases or USPTO material, not blogs alone.
6. Copyright: are circuit schematics, PCB layouts and firmware protected in the US, and what is not (the circuit's function)? Cite the Copyright Office or case law.
7. Shipping: USPS/UPS/FedEx rules for shipping devices with and without batteries (alkaline vs lithium).
8. Ohio: vendor's licence, sales tax on repair labour for tangible personal property, and any state rules for accepting customers' goods for repair (bailment, unclaimed items).

CANDIDATES (sources to consult first, then widen)
eCFR Title 47 Part 15; FCC OET Knowledge Database; EUR-Lex; UK gov.uk product-safety guidance; USPTO TMEP; US Copyright Office Compendium; Ohio Department of Taxation; Ohio Revised Code; carrier hazardous-materials guides.

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".
Table columns: topic · rule (section) · applies? (yes/no/depends on …) · action · FORM or LAWYER/ACCOUNTANT/BROKER · source URL · retrieved-on · status.

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.
You are not giving legal advice; say so once, then be as specific as the sources allow.

STOP CONDITION
Stop when all eight questions have a row with a primary source or an explicit "no primary source found".
```

### B8 — Time tracking and task management

```text
TITLE: Time tracking and project/task management for a solo consultant-maker

WHY IT MATTERS
The owner bills consulting and post-production by time, and builds pedals as jobs. He is autistic and finds navigating many tools costly; one place to look is worth more than features.

OBJECTIVE
Decide whether ERPNext Projects + Timesheets is enough, or whether a separate open-source tracker earns its place.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).

QUESTIONS
1. Can ERPNext Timesheets bill time straight into a Sales Invoice with no custom code? Cite docs.
2. Kimai, solidtime, ActivityWatch, Traggo: licence, last release, invoice export, mobile/desktop timers.
3. Plane, Vikunja, Focalboard, Leantime, OpenProject, WeKan: licence (note any open-core or licence change), last release, RAM. (Suspicion: Focalboard is no longer actively maintained as a standalone product.)
4. Which task tools were designed with neurodivergent users in mind or have published accessibility statements? (Leantime claims this — verify.)
5. Which combinations give a single daily view of "what is due and what is running" without opening a second app?
6. Which tools sync two-way with ERPNext or expose webhooks usable from n8n?
7. What is the export path (CSV/JSON/Markdown) of each?
8. For a single user, what do people actually report abandoning after 3 months, and why?

CANDIDATES
ERPNext Projects/Timesheets; Kimai; solidtime; ActivityWatch; Plane; Vikunja; Leantime; OpenProject; Focalboard; WeKan; plain Markdown task files in Obsidian.

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.

STOP CONDITION
Stop when you can answer "one tool or two?" with a named choice and the reason.
```

### B9 — Knowledge base, SOPs and a single front door

```text
TITLE: Vault governance, publishing and one front door for a solo owner's knowledge base

WHY IT MATTERS
The owner keeps notes and procedures in Obsidian and several self-hosted apps. He is autistic; switching between apps and hunting through folders is a genuine access barrier. A single start page is a requirement, not a nicety.

OBJECTIVE
Recommend (a) rules that keep one Obsidian vault usable for years, (b) an open publishing path for the public parts, (c) a single start page linking every system, and (d) an "if I am unavailable" document outline.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).
Note: Obsidian itself is free-but-proprietary. Report that honestly, list open alternatives that read the same Markdown files, and judge whether the plain-file format is a sufficient exit path.

QUESTIONS
1. Open alternatives that work on a folder of Markdown files: Logseq, SiYuan, Zettlr, VNote, Foam, SilverBullet — licence, last release, and what breaks when opening an Obsidian vault.
2. Publishing: Quartz, MkDocs Material, Hugo, Astro Starlight — which handle Obsidian links and embeds, and how is private content reliably excluded?
3. What vault conventions (folder depth, naming, front-matter fields, templates) are supported by evidence or long-term user reports as low-maintenance?
4. Start pages: Homepage, Homer, Dashy, Heimdall, Glance — licence, last release, RAM, and whether each can show service status.
5. How can a note link to an ERPNext or InvenTree record durably (URL patterns, IDs)?
6. Which published accessibility or cognitive-load guidelines apply to this (W3C COGA, others), and what do they concretely recommend?
7. What belongs in a one-page business-continuity note for a single-owner LLC? Cite a small-business authority.
8. How is the vault synced and backed up without a paid service (Syncthing, git, others) and what are the known data-loss traps?

CANDIDATES
Obsidian; Logseq; SiYuan; SilverBullet; Quartz; MkDocs Material; Homepage; Homer; Dashy; Glance; Syncthing.

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.

STOP CONDITION
Stop when (a)–(d) each have a concrete recommendation of at most ten lines.
```

### B10 — Newsletter, scheduling and media asset management

```text
TITLE: Open-source newsletter, booking and media-library tools for a one-person media business

WHY IT MATTERS
The owner does audio/video post-production and sells pedals. He needs a mailing list, a way for clients to book a call, and a searchable library of large media files — without three more servers to babysit.

OBJECTIVE
For each of the three needs, decide: self-host, use a hosted service with clean export, or do nothing yet.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).

QUESTIONS
1. Listmonk, Ghost, Keila, Mautic: licence, last release, and how each sends mail (own SMTP vs relay). What deliverability work falls on the owner?
2. US CAN-SPAM duties for a small sender: cite the FTC. What must every message contain?
3. Cal.com: current licence and which features are enterprise-only. Alternatives: Easy!Appointments, Rallly, others.
4. Immich, PhotoPrism, Nextcloud Memories, digiKam, ResourceSpace: which handle video and audio files well (not just photos), licence, RAM, and stability warnings from the maintainers.
5. For multi-hundred-gigabyte video projects, is a media manager on a small VPS realistic at all, or should assets stay on local/external disks with only an index online?
6. Which tools integrate with n8n or expose webhooks?
7. Export path for subscribers, bookings and asset metadata from each.
8. Monthly cost and upkeep of self-hosting each versus the cheapest hosted option with export.

CANDIDATES
Listmonk; Ghost; Keila; Mautic; Cal.com; Easy!Appointments; Rallly; Immich; PhotoPrism; ResourceSpace; digiKam.

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.

STOP CONDITION
Stop when each of the three needs has a "self-host / hosted / not yet" verdict with a reason.
```

### B11 — Reporting and n8n workflow reliability

```text
TITLE: Lightweight reporting on ERPNext data, and keeping n8n workflows from failing silently

WHY IT MATTERS
A solo owner automates hand-offs between self-hosted tools with n8n. An automation that fails quietly is worse than no automation. He also wants a handful of numbers (cash due, jobs open, stock below minimum) in one place.

OBJECTIVE
Decide whether a separate BI tool is justified, and define an inventory + failure-handling standard for n8n workflows.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).

QUESTIONS
1. What can ERPNext's built-in reports, dashboards and Number Cards show without any extra tool? Cite docs.
2. Metabase, Apache Superset, Redash, Grafana, Evidence: licence (flag Metabase's AGPL + paid tiers), RAM, last release, MariaDB support.
3. n8n's licence: is the Sustainable Use License open source? What does it restrict? What are the OSI-licensed alternatives (Node-RED, Activepieces, Windmill, Huginn, Kestra) and their trade-offs?
4. How should n8n workflows be version-controlled and backed up (export to JSON, git) on the community edition?
5. What is the documented pattern for error workflows, retries and idempotency in n8n?
6. How should credentials used by workflows be stored and rotated?
7. What minimal inventory record should exist per workflow (owner, trigger, systems touched, failure effect, last tested)?
8. How do users report n8n upgrades breaking workflows, and what upgrade routine avoids it?

CANDIDATES
ERPNext built-in reporting; Metabase; Superset; Redash; Grafana; Evidence; n8n; Node-RED; Activepieces; Windmill; Kestra.

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".
Also deliver: a workflow-inventory template as a table.

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.

STOP CONDITION
Stop when you can state whether n8n stays, and give the failure-handling standard in under one page.
```

### B12 — E-mail, domain and DNS

```text
TITLE: Business e-mail, domain registration and DNS that are not the weak link

WHY IT MATTERS
Every password reset, invoice and client conversation of a one-person LLC flows through one mailbox and one domain. Losing either stops the business.

OBJECTIVE
Decide between self-hosted mail and hosted mail with a clean export, and specify a domain/DNS setup that survives the loss of any one account.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).
Note: self-hosting outbound mail has well-known deliverability problems. If the evidence says a hosted provider is the responsible choice for a solo owner, say so and name it as the reasoned fallback.

QUESTIONS
1. Mailcow, Stalwart, Mailu, docker-mailserver, Mox: licence, last release, RAM, and reported deliverability to Gmail/Outlook from small VPS IP ranges.
2. Hosted providers with standard-protocol export (IMAP, JMAP, mbox) and custom domains: price, jurisdiction, and exit path. Include at least Fastmail, Migadu, Proton, mailbox.org, Purelymail.
3. What do Google's and Yahoo's bulk-sender rules (2024 onward) require even of small senders (SPF, DKIM, DMARC)?
4. A hybrid: self-hosted inbound + a relay for outbound — is it a sound compromise? Evidence?
5. Registrar and DNS: which registrars support registry lock or strong account security, and which DNS hosts offer an API usable for automated certificates?
6. How should the domain be protected against expiry or account loss (auto-renew, second contact, recovery codes stored offline)?
7. How are mail archives backed up and restored with each option?
8. What transactional-mail path should self-hosted apps (ERPNext, n8n, alerts) use?

CANDIDATES
Mailcow; Stalwart; Mailu; docker-mailserver; Mox; Fastmail; Migadu; Proton Mail; mailbox.org; Purelymail; deSEC; Cloudflare DNS; Hetzner DNS.

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.

STOP CONDITION
Stop when you can name one mail setup, one registrar + DNS host, and the recovery procedure if the owner loses access to each.
```

### B13 — Does ERPNext accounting fit a US single-member LLC?

```text
TITLE: Bookkeeping and tax-return fit — ERPNext vs simple open ledgers for a US single-member LLC

WHY IT MATTERS
The owner has chosen self-hosted ERPNext as the business system. Nobody has yet checked that its accounting produces what a US tax preparer needs, or whether it is far more system than a no-employee LLC requires.

OBJECTIVE
Determine whether ERPNext's accounting is a sound books-of-record for this LLC, or whether a simpler open-source ledger should hold the books while ERPNext handles operations only.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).

QUESTIONS
1. What records must a US single-member LLC (disregarded entity; also consider an S-corp election) keep, per IRS publications? Cite them.
2. Does ERPNext ship a usable US chart of accounts and can it produce Schedule C–aligned reports? Evidence from docs or the user forum.
3. How does ERPNext handle US sales tax by destination, and 1099-NEC tracking for contractors?
4. Bank feeds: what open or low-cost options import US bank transactions (OFX/CSV import, Plaid-based connectors, SimpleFIN)? Which are open source?
5. GnuCash, Beancount (+ Fava), hledger, Ledger, Akaunting, Frappe Books: licence, last release, reporting, and how each exports to an accountant.
6. What do US tax preparers typically accept from a small client (reports, CSV, a QuickBooks file)? Cite practitioner sources.
7. If the books live outside ERPNext, what is the cleanest one-way export of invoices and payments?
8. What is the documented ERPNext upgrade and maintenance burden for a solo admin over a year (version cadence, breaking changes)?

CANDIDATES
ERPNext Accounts; Frappe Books; GnuCash; Beancount + Fava; hledger; Akaunting; Dolibarr; (named fallback to evaluate honestly: a hosted bookkeeping product with full export).

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.
Tax statements must cite the IRS or the state and be labelled "confirm with accountant".

STOP CONDITION
Stop when you can answer: "books in ERPNext — yes or no?" with the two strongest reasons each way.
```

### B14 — Open data for component values, equivalents and substitutes

```text
TITLE: Open, redistributable data for electronic component value parsing, part-number aliases and substitutions

WHY IT MATTERS
An open-source (MIT) macOS inventory app decides whether a guitar-pedal build is "ready" by matching bill-of-materials lines to stock. Today it matches text, so "100n" and "0.1uF" do not match, and it knows nothing about acceptable substitutes. The fix needs data that can legally ship inside an MIT repository.

OBJECTIVE
Find data sources and reference implementations for: (1) parsing component values written in every common convention, (2) part-number aliases, (3) documented drop-in substitutes for transistors, diodes, op-amps and JFETs used in audio circuits.

HARD CONSTRAINTS
1. Open source first. Place every candidate on this ladder and report where it sits: OSI-approved licence (MIT, Apache-2.0, BSD, MPL, LGPL, GPL, AGPL) → source-available (BSL, ELv2, SSPL, "fair-code" — flag it) → free but proprietary → paid. A paid or closed option is acceptable only as a named fallback, with a stated reason why no open option works.
2. No AI features in the owner's own app; do not propose LLM calls, API keys or "assistant" features for it.
3. Unclassified, publicly available sources only. Nothing leaked, nothing behind a bypassed paywall.
4. Respect copyright: record provenance (URL, author, licence, date); never copy a whole page.
5. Label every claim VERIFIED (primary source opened), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. Ask no questions. The owner is autistic and administrative back-and-forth is costly: choose sensible defaults, state each in one line, and deliver one complete document.
Context: one owner, no employees, US (Ohio assumed). Existing plan: self-hosted ERPNext (MariaDB), InvenTree, n8n, Obsidian, Penpot, reached over Tailscale, on one small VPS (about 4 vCPU / 8 GB RAM, ~$10 a month).
Additional constraint: the app contains no AI and reads static JSON only. Deliverables must be data files or deterministic rules. Data licence must permit redistribution inside an MIT project — report the licence of every dataset.

QUESTIONS
1. Which open-source libraries parse component values (e.g. 4k7, 0.1uF, .022, 100n, 1M vs 1m, 2R2)? Licence and test-suite coverage of each.
2. Is there a published, citable specification of these notations (IEC 60062 RKM code, others)? What does it define?
3. E-series values (E6–E96): what is the authoritative source (IEC 60063) and an open implementation?
4. Which open datasets list semiconductor part numbers with package, pinout and key parameters? Check KiCad symbol libraries (licence terms and exception), Open Circuit / OSHW part libraries, Wikidata, others.
5. Is there any openly licensed transistor/op-amp cross-reference? If cross-reference books and vendor tools are proprietary, say so, and identify what can be derived lawfully from datasheet facts.
6. For audio-circuit staples (2N5088, 2N3904, BC108/BC549, J201, 2N5457, MPF102, TL072, JRC4558, LM308, 1N34A, 1N914/1N4148, germanium PNPs), what substitutions are documented by manufacturers or reputable engineering sources, and what parameter must be checked (hFE, Vp/Idss, pinout order)?
7. Pinout differences that break "drop-in" substitution (EBC vs CBE vs ECB): which source lists them reliably?
8. Capacitor and potentiometer attributes that affect interchangeability (dielectric, voltage rating, taper codes A/B/C and their US/EU/Asian differences): cite a standard or manufacturer note for each.

CANDIDATES
KiCad libraries; IEC 60062 / 60063; quantiphy; Python and Swift value-parsing libraries on GitHub; Wikidata; manufacturer datasheets and application notes; open SPICE model collections (check licences).

SCORECARD — one row per candidate, these columns
SPDX licence id · ladder position · last release (date) · maintainer health (active maintainers, bus factor, open-issue trend) · self-host cost (RAM, extra services) · data export / exit path · integration with ERPNext, InvenTree, n8n, Tailscale · open-core trap (which useful features are paid-only) · upkeep for a solo owner (hours a month, upgrade pain) · source URL · retrieved-on
For datasets, replace "self-host cost" with "size and format", and "integration" with "ease of converting to static JSON".

OUTPUT FORMAT
1. The scorecard table first.
2. Then at most one page of reasoning that answers the numbered questions in order.
3. Then a ranked recommendation: first choice, and one named fallback with the reason it is the fallback.
4. Then a short list: "what I could not verify".
Also deliver: a table of at least 40 value-notation test cases (input string → number + unit), which will become unit tests.

VERIFICATION DEMAND
Every table row needs a primary-source URL (project repository, official docs, licence file, regulator) and a retrieved-on date. Where you cannot open a primary source, write UNVERIFIED — do not guess. Candidate names given above are hypotheses, not facts: confirm each still exists and is maintained.

STOP CONDITION
Stop when the test-case table is complete and each of the three data needs has a named source with a confirmed licence, or an explicit "no open source exists".
```

---

## 5. Task D — schematic & confirmed-BOM census

### 5.1 What changed from the draft, and why

1. **A triage pass (D0) comes first.** About 70 entries are wiring diagrams or mods, and at least 3 are not circuits at all. Classifying and de-duplicating by name in one chat removes wasted census work before any batch runs.
2. **Revision pinning.** Most classic pedals exist in several revisions with different values. A BOM is only "confirmed" *for a named revision*, and the comparison with our extraction is only meaningful if the revision matches the image we hold.
3. **Tier per pedal, agreement per line.** "≥ 2 sources agree on every value" almost never holds for a whole pedal. Tier B now means two independent sources exist; each BOM line records whether they agree.
4. **Three long tables instead of one wide row**, so Code can ingest the reply by script.
5. **A time box per pedal**, so every batch finishes.

### 5.2 Batching plan

580 manifest rows (564 unique slugs; the 16 duplicated slugs keep both rows so the chat sees both files) → **29 batches** of ≤ 25, grouped by `effect_type`, alphabetical by slug inside a type (which keeps same-maker entries together). Slug lists live in the gitignored `docs/research/census/` folder; attach **one** `Bxx.csv` per chat.

| Batch | effect_type | Slugs |
|---|---|---|
| B01 | fuzz | 20 |
| B02 | fuzz | 20 |
| B03 | fuzz | 20 |
| B04 | fuzz | 20 |
| B05 | distortion | 25 |
| B06 | distortion | 25 |
| B07 | distortion | 25 |
| B08 | distortion | 22 |
| B09 | compressor | 15 |
| B10 | compressor | 14 |
| B11 | phaser | 18 |
| B12 | phaser | 17 |
| B13 | tremolo+reverb | 15 |
| B14 | chorus | 21 |
| B15 | flanger | 16 |
| B16 | delay | 18 |
| B17 | delay | 18 |
| B18 | delay | 18 |
| B19 | filter | 21 |
| B20 | filter | 21 |
| B21 | filter | 21 |
| B22 | filter | 18 |
| B23 | eq | 21 |
| B24 | eq | 21 |
| B25 | pitch | 24 |
| B26 | ring_mod | 16 |
| B27 | utility | 24 |
| B28 | utility | 23 |
| B29 | modification | 23 |
| **29 batches** | | **580** |

Run order is the batch number: fuzz and distortion first (simple, best documented, most likely to be built, best golden-set candidates); utility and modification last, and only for entries D0 marks as real circuits.

### 5.3 Prompt D0 — triage (run once, attach `schematic-manifest.csv`)

```text
TITLE: Triage of a 580-entry guitar-effect schematic list — classify and find duplicates (names only)

WHY IT MATTERS
A later, expensive research pass will look up each circuit's documentation. This pass removes entries that are not researchable circuits and groups entries that are the same circuit, so that effort is not wasted.

OBJECTIVE
Using only the attached CSV (columns: slug, name, source_category, effect_type, file_type, state) and public knowledge, classify every row and cluster duplicates. Do not research bills of materials in this pass.

HARD CONSTRAINTS
- Unclassified, publicly available sources only. No leaked or paywall-bypassed material.
- Label every judgement VERIFIED (you opened a source confirming it), REPORTED (a secondary source says so) or UNVERIFIED (inferred from the name). Most rows will be UNVERIFIED in this pass — that is expected; do not dress guesses up.
- Never invent a manufacturer or year. Write UNKNOWN.
- The names are scraped file titles and may be misspelled, abbreviated or wrong.
- Ask no questions; state any assumption in one line and proceed.

FOR EVERY ROW RETURN
slug · class · probable canonical name · probable maker/designer · cluster_id · confidence · note (≤ 12 words)

class is exactly one of:
  COMMERCIAL  – a commercially sold pedal or unit
  DIY         – an original DIY/community design
  CLONE       – a named clone or variant of a commercial circuit
  MOD         – a modification to another product
  WIRING      – a wiring/switching diagram, not a complete effect
  BLOCK       – a circuit fragment, app-note circuit or building block
  NOT-CIRCUIT – an article, paper, datasheet page, or digital/firmware product with no analog schematic to extract
  UNKNOWN

cluster_id: give the same id (K001, K002, …) to rows that are the same circuit or direct revisions/clones of one circuit. Leave blank if unique.

OUTPUT
1. One CSV code block with all 580 rows, in the input order.
2. A cluster table: cluster_id · circuit family · member slugs · which member is the best reference.
3. Counts per class.
4. The 30 entries most likely to have manufacturer-published documentation (service manuals, official schematics) — these become first candidates for a test set.

STOP CONDITION
All 580 rows classified. Do not start BOM research.
```

### 5.4 Prompt D1 — census (run once per batch, attach one `Bxx.csv`)

```text
TITLE: Guitar-effect circuit census — identification, public schematic sources and best-evidenced bill of materials

WHY IT MATTERS
The owner holds unverified, machine-read parts lists for about 580 guitar-effect schematics. Before trusting any of them to order parts or build, each circuit needs an identity and the best publicly evidenced bill of materials (BOM) to compare against.

OBJECTIVE
For each row of the attached CSV (columns: slug, name, source_category, effect_type, file_type, batch): (1) identify what circuit it is and which revision, (2) list the public sources of its schematic, (3) establish the best-evidenced BOM and grade the evidence.

HARD CONSTRAINTS
1. Open sources first. Prefer, in order: manufacturer/designer publications → openly licensed projects (CC0, CC-BY, CC-BY-SA, OSHWA-certified, open-hardware repositories on GitHub/GitLab/Codeberg) → circuit-analysis sites → commercial kit/PCB vendors' build documents → forum threads. Record each source's licence and whether it may be redistributed (Y / N / unclear).
2. Proprietary pages are evidence only. Record provenance and a paraphrased comparison. Do not copy a BOM table or reproduce a schematic from a proprietary page. Values of individual parts are facts and may be recorded with their source.
3. Unclassified, publicly available material only. Nothing leaked, nothing behind a bypassed paywall.
4. Every factual claim carries a URL and a retrieved-on date.
5. Every claim is labelled VERIFIED (you opened the primary source), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. NEVER invent a value to complete a BOM. An unknown line is written UNKNOWN.
7. The names are scraped file titles and may be wrong. If you cannot tell which circuit a row is, grade it X — do not guess.
8. Ask no questions. State assumptions in one line and proceed.
9. Time box: at most 8 searches per row. Stop that row at whatever tier the evidence supports.

REVISION RULE
Many pedals exist in several revisions with different values. Always name the revision or year a BOM belongs to. If sources describe different revisions, they do not "disagree" — list them as separate revisions.

EVIDENCE TIERS (exactly one per row)
A – Manufacturer-confirmed: official schematic or parts list, service manual, patent figure, or designer-published BOM.
B – Multi-source: at least two INDEPENDENT builder-vetted BOMs for the same revision. Sites republishing one original count as ONE source; say how you judged independence.
C – Single source: one builder/community BOM that is internally consistent (part count matches its schematic, values are standard).
D – Reconstructed: only a redrawn or traced schematic with no vetted BOM.
X – Not found, not identifiable, or not a complete circuit (say which).

OUTPUT — three CSV code blocks, then two short lists

TABLE 1 "circuits" — one row per slug:
slug, canonical_name, maker_or_designer, year, revision, family_lineage, variants_and_mods (names only), same_circuit_as (other slugs in this batch or well-known equivalents), tier, id_confidence (VERIFIED/REPORTED/UNVERIFIED), notable_parts (rare, obsolete or selection-critical parts: bucket-brigade chips, PT2399, matched or gain-selected transistors, germanium types, discontinued ICs), notes

TABLE 2 "sources" — one row per source:
slug, kind (schematic/BOM/analysis/manual/patent/forum), url, author_or_publisher, licence, redistributable (Y/N/unclear), revision_covered, retrieved_on, status (VERIFIED/REPORTED)

TABLE 3 "bom_lines" — only for tiers A–C, one row per part:
slug, revision, ref, type, value, tolerance_or_rating (only if a source states it), agreement (single / agree / differ), differing_value_and_source (if differ), substitute (only a DOCUMENTED substitute, with its source URL), source_urls, status

LIST 4 — "Could not find": slug and one line on what was searched.
LIST 5 — Golden-set candidates: up to 5 slugs from this batch whose tier A or B BOM, simple topology and clear revision make them the best test cases for a machine-extraction pipeline. One line of justification each.

OPTIONAL COMPARISON
If an extraction JSON is attached for a slug (keys: parts[] with ref/type/value, nets[], issues[]), add TABLE 6 "diff": slug, ref, extracted_value, confirmed_value, verdict (match / value-wrong / missing-in-extraction / extra-in-extraction / revision-difference), note. Then give counts per verdict. First state whether the extraction and the confirmed BOM appear to be the same revision; if not, say so and do not count revision differences as errors.

QUALITY CHECKS BEFORE YOU FINISH
- Every slug in the attached file appears exactly once in TABLE 1.
- No BOM line without a source URL.
- No value that is not a standard value without a note explaining it.
- Part count in TABLE 3 matches the part count of the cited schematic, or the difference is explained.

STOP CONDITION
All rows of the attached batch are graded A, B, C, D or X. Do not continue to other batches.
```

---

## 6. Run order

| Order | Chat | Depends on | Effort | Why now |
|---|---|---|---|---|
| 1 | **D0 triage** | manifest CSV | 1 chat, ~20 min of your time | Shrinks everything after it |
| 2 | **B14 value/equivalence data** | — | 1 chat | Unblocks C1/C2, the best trust-per-hour work |
| 3 | **D1 batches B01–B04 (fuzz)** | D0 | 4 chats | Source of golden-set candidates |
| 4 | *(Code, no chat)* lint + canonicaliser + 12-schematic pilot | 2, 3 | 1–2 days | First real accuracy number; decides re-extract vs review |
| 5 | **B3 backups** | — | 1 chat | Needed before any business data goes on the VPS |
| 6 | **B13 bookkeeping fit** | — | 1 chat | Could change the ERPNext plan — find out early |
| 7 | **B7 compliance** | — | 1 chat, then a lawyer hour | Gate before first sale |
| 8 | **B1 quote-to-cash** | 6 | 1 chat | Settles finding 8 (where customers live) |
| 9 | **B2 parts bridge** | 2 | 1 chat | |
| 10 | **B4, B12, B5** | 5 | 3 chats | Security and reliability basics |
| 11 | **D1 batches B05–B27** | 4 (only if the pilot says the data is worth confirming) | 23 chats, spread out | |
| 12 | **B6, B8, B9, B10, B11** | 8 | 5 chats | Useful, not urgent |
| 13 | **D1 batches B28–B29** | D0 | ≤ 2 chats | Only the entries D0 marks as real circuits |

**What I want back from you:** just the replies, pasted or saved anywhere — Code files them. For D0 and D1, the CSV blocks are what matter. Before step 4, pick (or let Code pick at random) the 12 pilot schematics.

---

## 7. Revision note for handoff v2

The handoff should (1) replace the connections-per-schematic hypothesis with the measured pin-coverage numbers and note that the DB chain-encodes nets; (2) correct the `issues[]` claim (they are in `design_notes`; confidence, pins and net names are what is lost); (3) say explicitly that the extraction DB does not feed the app today, so reviewers attack the right risk; (4) drop the "you do not have my files" framing when the reviewer runs in Code, and instead list which paths hold the data (the extractions live outside the repo, under `~/Documents/schematics/workshop/pipeline/`); (5) add D0 triage ahead of the census; (6) separate *fidelity* (extraction vs image) from *correctness* (image vs confirmed BOM) wherever "accuracy" is used; (7) record whether EU/UK sales are in scope, since that alone doubles the compliance work; (8) attach three extraction JSONs chosen by lint score — best, median, worst — so any outside reviewer sees the real spread.
