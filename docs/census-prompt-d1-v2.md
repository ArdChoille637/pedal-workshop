<!-- SPDX-License-Identifier: MIT -->
# Census prompt D1 — v2 (revised after Code's review of Fable's v1)

| | |
|---|---|
| **Status** | v2 — ready to relay; not yet run |
| **Version** | 2 |
| **Updated** | 2026-11-11 |
| **Supersedes** | prompt D1 in [`fable-reply-v1.md`](fable-reply-v1.md) §5.4 (kept there as the raw original) |
| **Parent** | [`handoff-fable-review-and-research.md`](handoff-fable-review-and-research.md) |

> **LIVING DOCUMENT.** Fold each batch reply's lessons back here, bump the version,
> and log it below. Outputs of this prompt contain third-party schematic titles and
> source-derived data: file them **only** under `docs/research/census/` (gitignored).

## What changed from v1, and why

| # | v1 | v2 | Why |
|---|---|---|---|
| 1 | ≤ 8 searches per row × ≤ 25 rows ≈ 200 searches in one chat | **≤ 5 searches per row, ≤ 15 rows** per batch (`make_census_batches.py --size 15`) | A research chat cannot sustain ~200 searches; batches would stop early with no record of where |
| 2 | No behaviour if the chat runs out of room | **Resume protocol**: finish whole rows only, then print `RESUME FROM: <slug>` + the unfinished slugs; never fill the rest with guesses | An unfinished batch must be resumable, not silently thin |
| 3 | "Values of individual parts are facts and may be recorded" — in practice, recording every line of one proprietary BOM reproduces the table | **Conservative copying rule** (below): full BOM lines only from sources whose licence permits reuse; for proprietary/unclear sources return counts + a *diff against our extraction* only | Whether a compiled parts list is protected is a legal judgement nobody has verified (prompt B7). Default to the safe side; revisit after B7 |
| 4 | Extraction JSON optional | **Attach `Bxx-extractions.json`** with every batch | The diff is now the main product for proprietary sources, and it is also what builds the golden set |
| 5 | 29 batches | **46 batches of ≤ 15**; re-cut after the D0 triage drops non-circuits | Smaller batches; D0 should remove ~70+ rows |

Open point (UNVERIFIED): whether the facts-vs-compilation line above is too cautious or not cautious enough. Prompt B7 owns that question; until it is answered, the outputs stay local.

---

▼ BEGIN PROMPT ▼

```text
TITLE: Guitar-effect circuit census — identification, public schematic sources and best-evidenced bill of materials

WHY IT MATTERS
The owner holds unverified, machine-read parts lists for about 580 guitar-effect schematics. Before trusting any of them to order parts or build, each circuit needs an identity and the best publicly evidenced bill of materials (BOM) to compare against.

ATTACHMENTS
1. Bxx.csv — the rows to research (columns: slug, name, source_category, effect_type, file_type, state, batch). At most 15 rows.
2. Bxx-extractions.json — for each slug, our machine-read data: {slug: {parts:[{ref,type,value,pins}], nets:[...], confidence, issues:[...]}}. A slug may be missing; then there is nothing to diff.

OBJECTIVE
For each row of Bxx.csv: (1) identify what circuit it is and which revision, (2) list the public sources of its schematic, (3) establish the best-evidenced BOM and grade the evidence, (4) compare it with our extraction.

HARD CONSTRAINTS
1. Open sources first. Prefer, in order: manufacturer/designer publications → openly licensed projects (CC0, CC-BY, CC-BY-SA, OSHWA-certified, open-hardware repositories on GitHub/GitLab/Codeberg) → circuit-analysis sites → commercial kit/PCB vendors' build documents → forum threads. For every source record its licence and whether it may be redistributed (Y / N / unclear).
2. COPYING RULE. List full BOM lines (TABLE 3) only from a source whose licence permits reuse (redistributable = Y). For any proprietary or unclear source: do NOT list its BOM. Instead give (a) the number of lines it lists, (b) its notable parts, and (c) — where an extraction is attached — TABLE 6, the diff against our extraction, quoting the source's value ONLY for refs where it differs from ours. Never reproduce a schematic image or a whole page.
3. Unclassified, publicly available material only. Nothing leaked, nothing behind a bypassed paywall.
4. Every factual claim carries a URL and a retrieved-on date.
5. Every claim is labelled VERIFIED (you opened the primary source), REPORTED (secondary source) or UNVERIFIED (inference or memory).
6. NEVER invent a value to complete a BOM. An unknown line is written UNKNOWN.
7. The names are scraped file titles and may be wrong. If you cannot tell which circuit a row is, grade it X — do not guess.
8. Ask no questions. State assumptions in one line and proceed.
9. TIME BOX: at most 5 searches per row. Stop that row at whatever tier the evidence supports.

RESUME PROTOCOL
Finish rows completely, in file order. If you are running out of room, stop after the last COMPLETE row. Output the tables for the completed rows, then end with exactly:
RESUME FROM: <first unfinished slug>
UNFINISHED: <comma-separated slugs>
Never pad unfinished rows with guesses.

REVISION RULE
Many pedals exist in several revisions with different values. Always name the revision or year a BOM belongs to. If sources describe different revisions, they do not "disagree" — list them as separate revisions.

EVIDENCE TIERS (exactly one per row)
A – Manufacturer-confirmed: official schematic or parts list, service manual, patent figure, or designer-published BOM.
B – Multi-source: at least two INDEPENDENT builder-vetted BOMs for the same revision. Sites republishing one original count as ONE source; say how you judged independence.
C – Single source: one builder/community BOM that is internally consistent (part count matches its schematic, values are standard).
D – Reconstructed: only a redrawn or traced schematic with no vetted BOM.
X – Not found, not identifiable, or not a complete circuit (say which).

OUTPUT — CSV code blocks, then two short lists
TABLE 1 "circuits" — one row per slug:
slug, canonical_name, maker_or_designer, year, revision, family_lineage, variants_and_mods (names only), same_circuit_as (other slugs in this batch or well-known equivalents), tier, id_confidence (VERIFIED/REPORTED/UNVERIFIED), notable_parts (rare, obsolete or selection-critical parts: bucket-brigade chips, PT2399, matched or gain-selected transistors, germanium types, discontinued ICs), notes

TABLE 2 "sources" — one row per source:
slug, kind (schematic/BOM/analysis/manual/patent/forum), url, author_or_publisher, licence, redistributable (Y/N/unclear), revision_covered, line_count (BOM sources), retrieved_on, status (VERIFIED/REPORTED)

TABLE 3 "bom_lines" — tiers A–C, ONLY from sources with redistributable = Y; one row per part:
slug, revision, ref, type, value, tolerance_or_rating (only if the source states it), source_url, status
(For every other source write one row: slug, "LINES WITHHELD — proprietary/unclear licence", source_url.)

TABLE 6 "diff" — one row per ref, only for slugs that have an extraction attached and a BOM source (any licence):
slug, ref, extracted_value, source_value (quote ONLY when it differs; otherwise "same"), verdict (match / value-wrong / missing-in-extraction / extra-in-extraction / revision-difference), note
First state per slug whether the extraction and the source appear to be the same revision; if not, say so and do not count revision differences as errors. Then give counts per verdict per slug.

LIST 4 — "Could not find": slug and one line on what was searched.
LIST 5 — Golden-set candidates: up to 3 slugs from this batch whose tier A or B BOM, simple topology and clear revision make them the best test cases for a machine-extraction pipeline. One line of justification each.

QUALITY CHECKS BEFORE YOU FINISH
- Every slug you completed appears exactly once in TABLE 1; every slug not completed is named in UNFINISHED.
- No BOM line in TABLE 3 without a source URL and redistributable = Y.
- No value that is not a standard value without a note explaining it.
- Part count in your source matches the part count of its cited schematic, or the difference is explained.

STOP CONDITION
Every row of the attached batch is graded A, B, C, D or X — or you have printed the RESUME block. Do not continue to other batches.
```

▲ END PROMPT ▲

---

## How Code will use the replies
1. File raw replies under `docs/research/census/replies/Bxx.md` (gitignored).
2. Parse TABLE 1/2/3/6 by script into a local `census.sqlite` next to the extraction DB.
3. Feed LIST 5 + TABLE 6 verdict counts into the golden-set selection (reply §2.4 of `fable-reply-v1.md`).
4. If `RESUME FROM` appears, re-cut a batch from `UNFINISHED` and relay again.

## Revision log
| Ver | Date | Change |
|---|---|---|
| 2 | 2026-11-11 | Code's review of Fable's v1 D1: time box 8→5 searches/row, batches 25→15, resume protocol, conservative copying rule + diff-first for proprietary sources, extraction bundle attached, local-only filing. |
| 1 | 2026-11-11 | Fable pass 1 (`fable-reply-v1.md` §5.4). |
