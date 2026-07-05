<!-- SPDX-License-Identifier: MIT -->
# Pedal Workshop

A **native macOS app** for guitar-pedal builders: a parts inventory manager,
a build analyzer, a schematic image browser, and live supplier price lookup.

Built with **SwiftUI + Swift 6**. No backend, no accounts, no cloud — the app
reads and writes plain JSON on your Mac.

**Ports:** the same app is being ported to other platforms — a **Flet (Python)
desktop** app in [`python/`](python/) and a **native Android (Kotlin/Compose)**
app in [`android/`](android/). All three share the same data model, Build
Analyzer algorithm, and Mouser search, so they behave identically.

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
- **Schematic browser** — grid + detail viewer for images and multi-page PDFs
  (PDFKit) with zoom and quick open / reveal in Finder.
- **Supplier price lookup** — live keyword search against Mouser (free,
  Keychain-stored API key) from a dedicated **Price Lookup** tab or per
  inventory part; other suppliers listed for reference/manual entry.

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
| Your schematic library (yours to provide) | any folder; index it with pipeline/tools |

The repo ships an **empty** schematic library — Pedal Workshop does not
redistribute anyone's schematics. To load your own:

```sh
python3 pipeline/tools/generate_native_index.py   # build the index (schematics.json)
python3 pipeline/tools/package_schematics.py       # copy the files into the app bundle
cd native && ./launch.sh                            # rebuild
```

The app reads schematic files **only from its own bundle**, never from
`~/Documents` — so it never asks for Documents-folder permission and stays
self-contained.

## Repository layout

```
native/      the macOS app (SwiftUI) + WorkshopCore Swift package
python/      Flet (Python) desktop port — see python/README.md
android/     native Android (Kotlin + Jetpack Compose) port
pipeline/    optional offline schematic→KiCad batch tooling (see pipeline/README.md)
seeds/       generic default inventory / suppliers / sample project
```

## License

[MIT](LICENSE) © Michael Ray Gregory
