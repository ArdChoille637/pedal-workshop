<!-- SPDX-License-Identifier: MIT -->
# Pedal Workshop

A **native macOS app** for guitar-pedal builders: a parts inventory manager,
a build analyzer, and a schematic browser with OCR'd bills of materials and
live supplier price lookup.

Built with **SwiftUI + Swift 6**. No backend, no accounts, no cloud — the app
reads and writes plain JSON on your Mac.

> **Scope:** Pedal Workshop is a self-contained desktop app. It contains **no
> AI/LLM features** — it only reads static JSON. The separate, optional
> [`pipeline/`](pipeline/) directory is offline batch tooling that turns a
> personal schematic library into structured data (KiCad projects + a SQLite
> DB); it is never invoked by the app.

---

## Features

- **Inventory** — track components with min-stock alerts, barcode entry
  (GS1-128 / MH10.8.2), category/value sorting, and quick +/- adjustments.
- **Build Analyzer** — per-project BOM demand vs. on-hand stock, with
  Ready / Almost-Ready-Not-Available states and value normalization
  (`4k7`, `470R`, `Ω` all understood).
- **Schematic browser** — grid + detail viewer (images and multi-page PDFs via
  PDFKit), with an OCR-extracted BOM side panel and one-click
  "create project from schematic".
- **Supplier price lookup** — live search against Mammoth and Mouser
  (Keychain-stored API key); other suppliers listed for reference.

## Requirements

- macOS 26+ and Xcode 26+
- [XcodeGen](https://github.com/yonsg/XcodeGen) (`brew install xcodegen`) —
  the Xcode project is generated from [`native/project.yml`](native/project.yml)

## Build & run

```sh
cd native
./launch.sh        # generates the project if needed, builds, installs to /Applications, launches
```

`launch.sh` is the single front door. It runs `xcodegen generate` on a fresh
clone, does an incremental Debug build of the `PedalWorkshop-macOS` scheme,
installs **Pedal Workshop.app** to `/Applications`, and opens it.

## Where your data lives

| Data | Location |
|---|---|
| Your inventory, projects, BOMs (live) | `~/Library/Application Support/PedalWorkshop/*.json` |
| First-run seed defaults (shipped) | `native/Sources/WorkshopCore/Resources/*.json` |
| Your schematic library (yours to provide) | any folder; point the app at it and **Rescan** |

The repo ships **empty** schematic seeds — Pedal Workshop does not redistribute
anyone's schematic library. Populate your own with the app's
**Settings → Rescan Schematics Folder**, or with
[`pipeline/tools/generate_native_index.py`](pipeline/tools/generate_native_index.py).

## Repository layout

```
native/      the macOS app (SwiftUI) + WorkshopCore Swift package
pipeline/    optional offline schematic→KiCad batch tooling (see pipeline/README.md)
seeds/       generic default inventory / suppliers / sample project
```

## License

[MIT](LICENSE) © Michael Ray Gregory
