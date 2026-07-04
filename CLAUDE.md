# Pedal Workshop — agent guide

Native **macOS SwiftUI** app for guitar-pedal builders: inventory, build
analyzer, schematic browser. Plus an **optional, separate** offline pipeline
that converts a schematic library into KiCad projects + a SQLite DB.

## HARD boundary — no AI in the app
The app is a plain inventory/schematic-browser tool. It reads **only static
JSON** and contains **zero AI/LLM/vision code**. All AI/vision schematic
processing is **external batch tooling** under `pipeline/`, driven by separate
Claude/Gemini sessions — never wire LLM calls, API keys, or "AI assistant"
features into the app. The app never imports or invokes a `pipeline/` module.

## Layout
- `native/` — the product. SwiftUI app + `WorkshopCore` Swift package.
  - `App/macOS/` — the single app target's entry point + navigation.
  - `App/Shared/Views/` — SwiftUI feature views.
  - `Sources/WorkshopCore/` — models, services (`WorkshopStore`, `BuildAnalyzer`,
    `SupplierSearch`), persistence (`LocalDataStore`), and bundled JSON seeds.
- `pipeline/` — offline schematic→KiCad tooling (see `pipeline/README.md`).
- `seeds/` — generic default data mirrored into the app's bundle Resources.

## Build
```sh
cd native && ./launch.sh     # xcodegen (if needed) → build → install to /Applications → launch
```
The Xcode project is generated from `native/project.yml` by **XcodeGen** and is
gitignored — `project.yml` is the source of truth. macOS-only (one target,
scheme `PedalWorkshop-macOS`).

## Data model
- Live user data: `~/Library/Application Support/PedalWorkshop/*.json`
  (inventory, projects, BOMs). Seeded on first run from bundle Resources.
- State ownership: `WorkshopStore` (`@Observable @MainActor`) is the **only**
  gateway between views and persistence (`actor LocalDataStore`). Views call
  async store methods; never reach past the store into `LocalDataStore`.
- Schematic index/metadata seeds ship **empty** in git (they'd otherwise leak
  home paths + copyrighted OCR text). Regenerate locally with
  `pipeline/tools/generate_native_index.py` + `analyze_schematics.py`, or the
  app's **Settings → Rescan Schematics Folder**.

## Architecture notes
- `BuildAnalyzer` aggregates per-project BOM demand by `StockKey` vs. on-hand
  stock; `normalizeValue` handles `Ω`/`470r`/`4k7` forms.
- `SupplierSearch` currently searches Mammoth + Mouser (Keychain key); other
  seeded suppliers are reference-only.
- Barcode parsing (GS1-128 / MH10.8.2) lives in `WorkshopCore`, unit-testable.
