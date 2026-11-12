<!-- SPDX-License-Identifier: MIT -->
# Handoff → Fable: adversarial review + research-prompt factory

| | |
|---|---|
| **Status** | v1 — drafted, NOT yet relayed to Fable |
| **Version** | 1 |
| **Updated** | 2026-11-11 |
| **Companion** | `research/schematic-manifest.csv` (580 slugs; **local-only, gitignored** — it lists third-party schematic titles. Attach it to Fable and to every schematic/BOM research chat) |

> **LIVING DOCUMENT.** Every Fable/research reply gets filed in the *Reply log*
> at the bottom, the verdict is stamped inline (`✔ v2 PASS-1 VERDICT: …`) on the
> item it resolves, and the version + Revision log are bumped. Never relay this
> as a one-shot.

## How to use (Michael — 3 steps)

1. Open a Fable chat. Attach `research/schematic-manifest.csv`.
2. Paste everything between **▼ BEGIN PROMPT** and **▲ END PROMPT**.
3. Paste Fable's replies back to Code. Code files them in the Reply log, folds the
   verdicts in, bumps the version, and prepares the next relay.

Fable's deliverable is **research prompts** (Part B and D) — each one is a
self-contained brief you then paste into its own research chat. Code files those
replies the same way.

---

▼ BEGIN PROMPT ▼

# Role

You are **Fable**, acting as (1) an **adversarial reviewer** who tries to break my
plans, and (2) a **research-prompt writer** who turns the weak spots into
research briefs I will run in separate research chats. You do not have my files;
everything you need is in this message and the attached CSV. If something is not
here, say **UNKNOWN** and list it as a question — do not guess.

## Ground rules (apply to everything you write)

1. **Open source first, always.** For every tool, library, dataset, or service
   you propose or ask a research chat to evaluate, use this ladder and make the
   research chat report where each candidate sits:
   OSI-approved licence (MIT/Apache-2.0/BSD/MPL/LGPL/GPL/AGPL) → source-available
   (BSL/ELv2/etc. — flag) → free-but-proprietary → paid. A paid/closed option is
   acceptable **only** as a named fallback with a stated reason no open option
   works. Every candidate must also report: SPDX licence id, last release date,
   maintainer health (bus factor, open-issue trend), self-host requirements,
   **data export/exit path**, and an **open-core trap check** (which useful
   features are paid-only).
2. **No AI inside the Pedal Workshop app.** The app reads static JSON only. AI
   work (vision, extraction, research) lives in the offline `pipeline/`. Reject
   any suggestion that adds LLM calls, API keys, or "assistant" features to the app.
3. **Unclassified, publicly releasable sources only.** No leaked, paywall-bypassed,
   or CUI material. Cite every factual claim with a URL + retrieval date.
4. **Copyright:** schematics and published BOMs are mostly someone else's work.
   Research chats record **provenance (URL, author, licence, date)**, never
   reproduce a schematic or copy a whole page. Redistribution status must be
   recorded per source.
5. **Label epistemic status.** Every claim is `VERIFIED` (primary source seen),
   `REPORTED` (secondary source), or `UNVERIFIED` (inference/memory). Anything I
   state below as a "known weakness" is a **hypothesis to attack**, not gospel.
6. **Fewest questions.** I'm autistic; administrative back-and-forth and
   navigating many files is a real cost. Pick sensible defaults, state them in one
   line, proceed. Ask at most **three** blocking questions, all up front, only if
   a wrong guess would waste real work. Deliver everything as **one document in
   the order given under "Output contract."**

# Context pack

## Who / what
Michael Ray Media, LLC (MRM-LLC): one owner, **no employees**, three lines —
media post-production, acoustic consulting/contracting, hardware invention
(incl. guitar pedals and a small electronics shop). Ohio-based *if formed
there* (**UNCONFIRMED** — treat as an assumption to verify).

## The back-office stack I've already chosen (attack it)
Self-hosted, sovereign: **ERPNext (MariaDB) + InvenTree + Penpot + Obsidian + n8n
+ Tailscale**, on a ~$10/mo VPS (Hetzner CX33 class). A prior 56-agent audit of
the blueprint's 60 claims found 50 confirmed / 10 partially true / 0 fabricated.
Corrections that already stand — don't re-litigate, but do challenge *fit*:
ERPNext requires MariaDB in production (Postgres not production-ready);
ERPNext is GPL-3.0 and HR is the separate `frappe/hrms` app; Odoo Community has
BOM/routing but its general ledger is Enterprise-only (disqualifying);
Tailscale state encryption is opt-in (`--encrypt-state`, TPM 2.0); Ohio's
E-Verify duties (ORC Ch. 4151, effective 2026-03-20) trigger only at first hire.
Two open facts: **State of Formation is not recorded**, and **I have not decided
whether jobs/clients live in ERPNext or in the Workshop app** (see Part C).

## Pedal Workshop (the app + pipeline) — repo `github.com/ArdChoille637/pedal-workshop`, MIT
**App** — native macOS SwiftUI (Swift 6) + `WorkshopCore` SPM lib; `actor
LocalDataStore` persists plain JSON in `~/Library/Application Support/
PedalWorkshop/`; `@Observable WorkshopStore` is the only view→persistence gateway.
Features: parts inventory (min-stock, GS1-128/MH10.8.2 barcode entry), Projects
+ BOM, **Build Analyzer** (Ready / ARNA tiers: aggregates BOM demand per
`StockKey` vs on-hand, `normalizeValue` handles `Ω`/`470r`/`4k7`, skips optional
rows), read-only schematic image/PDF browser, Mouser price search (Keychain key;
other suppliers reference-only because Tayda/LMS/Mammoth block scripted access).
**Just added (2026-11-11, unverified in a running app — no Xcode on that Mac):**
`Client` + `Job` (build/repair/mod; status, quote, deposit, due date; optional
`projectId` link) in local-only `clients.json`/`jobs.json`, no bundle seed.

**Pipeline (offline, separate from the app)** — vision-extracts each schematic
image into `extractions/<slug>.json` (parts + nets), then `netlist_to_kicad.py`
→ openable KiCad project + draft ngspice deck, `build_database.py` →
`pedal_schematics.db`, `manifest.py` tracks state. Extractions were produced by
**Gemini Flash** in bulk; **all are `review` state = nobody has verified any**.

## Measured facts about the extraction DB (read-only query, 2026-11-11)
- 565 schematics · **24,286 components** · **12,803 connections**
  (connections ≈ 22/schematic vs ≈ 43 components/schematic — hypothesis: the
  netlist is *incomplete*; ATTACK THIS FIRST).
- Types: resistor 10,414 · capacitor 6,086 · potentiometer 1,335 ·
  transistor 1,238 · diode 1,204 · opamp 938 · jack 893 · ic 579 · switch 492 ·
  jfet 392.
- 8 components with empty value; 3 schematics with **zero** components.
- Value strings are **un-normalized and mixed-convention**: `0.01u`, `1uF`,
  `47p`, `620` (unit-less), `324` (an LM324 stored as a bare number), `J113`,
  `NE571`, jack `value='unknown'`, jack `value='POWER'` (a role, not a value).
- DB schema is lossy: `components(name,type,value)` and
  `connections(from_pin,to_pin)` — **no pin numbers on parts, no tolerance /
  voltage rating / package, no confidence, no source/provenance, no
  human-verified flag.** The richer `issues[]` the extractors logged lives only
  in the JSON files.
- Corpus: **580 manifest entries (574 awaiting review, 6 pending extraction)** (distortion 97,
  filter 81, fuzz 80, delay 54, utility 47, eq 42, phaser 35, compressor 29,
  pitch 24, modification 23, chorus 21, flanger 16, …). Source library was
  scraped from a public schematic archive; **originals are third-party works.**

# Task A — Adversarial review (do this first)

Try to break each target. For every finding give: **target · claim attacked ·
evidence/reasoning · severity (blocker/major/minor) · cheapest test that would
settle it · recommended fix.** Rank by severity × cheapness-to-fix.

Targets, in priority order:
1. **Extraction trustworthiness.** Is the DB fit to drive BOM, inventory demand,
   and KiCad output? What's the error model for VLM-read schematics (value
   misreads, 5/6/8 confusions, missed junction dots, reference-designator
   duplicates, off-sheet nets, hand-drawn scans)? Is "human review of 565
   items" even a feasible process — design a **sampling + golden-set** protocol
   (sample size, stratification by effect_type/file_type/scan quality, the
   metrics: per-component value accuracy, net-connectivity F1, BOM line-item
   recall/precision, and a stop/ship threshold).
2. **Schema & data model.** What must the DB/JSON gain to be *correct*, not just
   present (canonical value fields: numeric + unit + tolerance + rating +
   package; pin-level connectivity; provenance; confidence; verified-by/date;
   per-source BOM tiers)? Propose a migration that doesn't discard the
   `issues[]` the extractors already wrote.
3. **Build Analyzer correctness.** Where does value-matching fail in the real
   world (E-series snapping, ±5/1% equivalence, film vs electrolytic vs MLCC
   caps, pot taper and shaft, transistor/diode/op-amp equivalents and
   substitutions, sockets, jacks/switches by form-factor, enclosure fit)? What
   would make a "Ready to build" verdict **wrong**?
4. **Clients/Jobs design** (just built): is a second system of record for
   customers a mistake given ERPNext is already the plan? Compare
   *Workshop-local* vs *sync to ERPNext (Customer/Sales Order/Quotation)* vs
   *InvenTree for parts only*; recommend one with an exit path. Check privacy:
   PII in a local JSON file, backup, and the "never in the public repo" rule.
5. **Legal/regulatory exposure of selling pedals.** Cloning commercial designs
   vs trademarks/trade dress/copyright in schematics & layouts; FCC Part 15 /
   CE/UKCA, RoHS/WEEE, battery/lithium shipping, product-liability insurance,
   Ohio sales tax/marketplace rules, repair-customer liability. Mark each
   `VERIFIED/REPORTED/UNVERIFIED` and say which need a lawyer vs a form.
6. **The back-office stack.** Single points of failure (one VPS, Tailscale
   dependency, backups/restore tested?), operational burden for a solo owner,
   security posture, vendor/licence risk, what is over-built for a no-employee
   LLC and what is conspicuously missing.
7. **Process risk:** token/quota constraints, reliance on one extraction
   engine, reproducibility of the pipeline, bus-factor-of-one on the owner.

# Task B — Research-prompt factory for the back office (open source first)

Produce a **numbered set of research prompts** (target 10–14; merge/split as you
see fit) for additions to the back office. Each prompt must be **paste-ready
and self-contained** (a research chat has no context), and contain, in this
order: **Title · Why it matters to MRM-LLC (2 lines) · Objective · Hard
constraints (open-source-first ladder + my 6 ground rules, restated) · Questions
to answer (≤8, each answerable & falsifiable) · Candidate list to evaluate +
"find others" instruction · Per-candidate scorecard fields (SPDX licence, last
release, maintainer health, self-host cost/RAM, data export, integration with
ERPNext/InvenTree/n8n/Tailscale, open-core trap, solo-owner ops burden) ·
Output format (table first, then ≤1 page of reasoning, then a ranked
recommendation with a named fallback) · Verification demand ("every row needs a
primary-source URL + date; mark UNVERIFIED rather than guess") · Stop
condition.**

Seed topics — **candidates listed are starting hypotheses, not facts; the
research chat must verify each and widen the field**:
- Client/job/quote/invoice flow for a one-person shop: ERPNext modules vs
  Dolibarr vs Akaunting vs Invoice Ninja vs Crater vs EspoCRM; e-signature
  (Documenso, OpenSign); proposals.
- Parts/BOM/PLM: **InvenTree ⇄ Pedal Workshop bridge**, Part-DB, PartKeepr,
  Kitspace, KiBot, KiCost-style price roll-ups; supplier-API access that
  respects ToS (Mouser/DigiKey/LCSC/Octopart-alternatives).
- Backups & recovery: restic/borg/Kopia + offsite (Backblaze B2/Hetzner
  Storage Box), **tested-restore runbook**, DB-consistent snapshots for
  MariaDB/Postgres.
- Identity & secrets: Vaultwarden, Authentik/Keycloak/Authelia, SSH CA,
  Tailscale vs Headscale vs NetBird/WireGuard (self-hosted control plane).
- Observability: Uptime Kuma, Netdata/Prometheus+Grafana, log hygiene, alerting
  to a phone without a SaaS.
- E-commerce for physical pedals: Medusa, Saleor, Vendure, WooCommerce,
  Shopify-alternatives; **payments without a closed gateway** (BTCPay Server,
  Stripe as named fallback), tax (Ohio/destination-based), shipping labels
  (open options), returns/RMA for repairs.
- Compliance register as code: FCC/CE/RoHS/WEEE per product, insurance,
  license-for-clone-designs checklist — and which items are *forms* vs *lawyer*.
- Time tracking & billing for consulting/contracting; project/task tools
  (Plane, Focalboard, Vikunja) vs doing it in ERPNext Projects.
- Docs/knowledge/SOP: Obsidian-vault governance, publish pipeline (Quartz),
  link to ERPNext records; accessibility of the whole UI for an
  autistic, low-navigation owner (single front door).
- Marketing/media-ops: Ghost/Listmonk newsletter, Cal.com scheduling,
  Immich/PhotoPrism for asset management (Michael does audio/video post).
- Data & analytics: Metabase/Superset on ERPNext; **n8n workflow inventory +
  failure handling**.
- Email/domain/DNS hosting that isn't the weak link (Mailcow/Stalwart vs
  hosted-with-export).

# Task C — Make the Workshop app more accurate and more powerful

Separate **accuracy** (what makes its outputs *right*) from **power** (what it
newly lets me do). Respect the no-AI-in-app rule — AI may build the *data*
offline; the app stays static-JSON-driven. For each proposal give: **problem ·
change · where it lives (app vs pipeline vs data) · how we'd measure the
improvement · cost (S/M/L) · open-source tools it can reuse.**

Hypotheses to attack and extend (don't just accept them):
- **Accuracy:** canonical value model (numeric+unit+tolerance+rating+package);
  an E-series/equivalence/substitution table (open data, e.g. transistor,
  diode, op-amp cross-refs) that the Build Analyzer consults; a **verification
  status** on every BOM line (`extracted` → `human-checked` → `source-confirmed`)
  surfaced in the UI so "Ready" can show *how confident*; golden-set regression
  tests that fail the build when extraction quality regresses; a confirmed-BOM
  tier model (see Task D) feeding the app as a static JSON per project.
- **Power:** BOM/inventory import-export (CSV, KiCad BOM, InvenTree), price
  roll-up and "cheapest compliant build" using open supplier data, shopping
  list that groups by supplier, enclosure/drill-template data, cost + margin
  per job, build-history/serials for repairs, label/QR printing, a search
  across 24k extracted parts ("which pedals use a J113?") from the existing
  `query_topology.py`, an inventory-aware "what can I build from stock" view.
- **Robustness:** repo is MIT and public — confirm nothing from the
  copyrighted corpus or customer PII can leak (gitignore, pre-commit
  secret/PII scan, packaging).

Close Task C with a **prioritized 10-item roadmap** and the **three** changes
that would most improve trust in the numbers per hour of work.

# Task D — The schematic + confirmed-BOM census (embed this as research prompt #D)

Write this out as the final, polished, paste-ready research prompt — **start from
the draft below, improve it, and split it into batches** (suggest ≈25 slugs per
chat, grouped by `effect_type`, so each chat finishes). Keep every constraint.

> **DRAFT RESEARCH PROMPT — Pedal schematic & confirmed-BOM census**
>
> **Objective.** For each pedal/circuit in the attached list (CSV columns: slug,
> name, source_category, effect_type, file_type), (1) identify **what circuit it
> actually is** (canonical name, original manufacturer/designer, year, circuit
> family/lineage, and known variants), (2) find **every public source of its
> schematic**, and (3) establish the **best-evidenced confirmed bill of
> materials (BOM)** — then compare it to our unverified machine-extracted data.
>
> **Open-source-first rule.** Prefer sources with open licences (CC-BY, CC0,
> OSHWA-certified, open-hardware repos on GitHub/GitLab/Codeberg, community
> projects that publish BOMs under a permissive licence). Report every source's
> licence/redistribution status. Proprietary builder-site BOMs (e.g.
> commercial PCB houses, kit vendors) are allowed as **evidence** but you must
> record only provenance and a *paraphrased* comparison, never copy a page.
>
> **"Confirmed BOM" has a ladder — assign exactly one tier per pedal:**
> - **A — Manufacturer-confirmed:** official schematic/parts list, service
>   manual, patent exhibit, or designer-published BOM.
> - **B — Multi-source agreed:** ≥2 *independent* builder-vetted BOMs (not
>   copies of each other) that agree on every value; list any component where
>   they differ.
> - **C — Single source:** one builder/community BOM, verified internally
>   consistent (parts count vs. schematic, standard values).
> - **D — Reconstructed:** only our machine extraction or a redrawn schematic.
> - **X — Not found / ambiguous (state why).**
> Independence matters: three sites republishing one original is **one** source.
>
> **Per pedal, return one row with these fields:** slug · canonical name ·
> manufacturer/designer · year · lineage/family · variants & mods (names only) ·
> schematic sources (URL, author, licence, redistributable Y/N, retrieved-on) ·
> BOM sources (URL, tier, licence, retrieved-on) · **confirmed BOM** as
> `ref,type,value,tolerance/rating notes,notes` (only if tier A–C) ·
> **disagreements between sources** (ref: valueA vs valueB, with sources) ·
> **notable parts** (rare/obsolete: e.g. BBD, PT2399, matched transistors,
> specific germanium types) and a flag for no-longer-made parts + a
> *documented* substitute with source · confidence (`VERIFIED/REPORTED/
> UNVERIFIED`) · notes.
>
> **Method.** Work in batches; for each pedal search (a) designer/manufacturer
> documentation, (b) open-hardware repos and PCB/build-doc sites, (c) circuit
> analysis sites (teardowns that explain the design), (d) forum threads with
> measured/verified builds — *treat forum posts as tier C at best, and flag
> anything unverifiable.* Cross-check parts count against the schematic and flag
> impossible values. Where several pedals are the **same circuit under
> different names**, say so and cluster them (this saves effort and exposes
> duplicates in our corpus).
>
> **Our-data comparison (if I supply the extraction JSON for a slug):** diff
> our extracted BOM vs your confirmed BOM → counts of match / value-wrong /
> missing / extra, listing each discrepancy. This builds the golden set.
>
> **Hard rules.** No leaked or paywall-bypassed material. Cite URL + date for
> every claim. **Never invent a value to complete a BOM** — leave the line
> `UNKNOWN`. Do not reproduce schematics or copy BOM tables verbatim from
> proprietary pages. Stop a pedal at tier D/X rather than speculating.
>
> **Output.** (1) A single CSV/table per batch, one row per pedal; (2) a second
> table of cross-pedal duplicates/lineages; (3) a short "what I couldn't find"
> list; (4) the 5 pedals whose tier-A/B BOMs would make the best **golden set**
> for testing the extraction pipeline, with a justification.

# Output contract (what you hand back, in this order)

1. **Assumptions & ≤3 blocking questions** (or "none").
2. **Task A findings** — ranked table, then the sampling/golden-set protocol.
3. **Task C roadmap** — prioritized 10 items + the top-3 trust wins.
4. **Task B prompts** — the numbered set, each paste-ready.
5. **Task D prompt** — final polished version, with the batching plan
   (batch → slugs by `effect_type`).
6. **Run order:** which research chats to run first, which depend on others,
   rough effort for each, and what you'd want back from me.
7. **Revision note:** one paragraph on what you'd change in *this handoff* so
   v2 is sharper.

▲ END PROMPT ▲

---

## Open items before / while relaying
- [ ] Attach `research/schematic-manifest.csv` to Fable.
- [ ] Decide whether to also attach 3–5 representative `extractions/<slug>.json`
      files (Fable can then judge `issues[]` quality) — Code can pick them.
- [ ] Confirm **State of Formation** (affects Task A.5 and the Ohio analysis).
- [ ] Verify the new Clients/Jobs view in a real Xcode build (not done).
- [ ] Not yet measured: extraction field-level accuracy against any ground
      truth — Task A.1 / Task D produce the first real number.

## Revision log
| Ver | Date | Change |
|---|---|---|
| 1 | 2026-11-11 | Initial handoff drafted by Code: tasks A–D, ground rules, measured DB facts, manifest CSV. |

## Reply log (file Fable's / research-chat replies here — raw, then verdict)
*(empty — nothing relayed yet)*
