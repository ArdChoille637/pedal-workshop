# Pedal Workshop

> A full-stack inventory, build management, and prototyping tool for boutique guitar and bass pedal makers.

Built for the real workflow of a small-batch effect pedal shop — tracking component stock, managing builds, browsing a schematic library, and looking up live supplier prices.

---

## What it does

### Inventory
- Component database with category, value, package, MPN, location, and min-stock alerts
- Bulk entry via USB barcode scanner (DigiKey / Mouser bag labels parsed automatically)
- Quantity +/− directly from the list

### Schematics Library
- Browses 800+ guitar effect schematics (GIF, JPG, PNG, PDF) organized by effect type
- OCR-based BOM extraction: resistors, capacitors, ICs, transistors, diodes parsed from each image
- "Add all parts to project" from any schematic detail view

### Projects & BOMs
- Project tracker with Bill of Materials per build
- **Build Analyzer** classifies each project:
  - ✅ **Ready** — all parts in stock
  - 🟡 **ARNA 1–3** — 1–3 parts to acquire
  - 🔴 **ARNA 4+** — significant sourcing required

### Supplier Price Lookup
- Live search across **Tayda Electronics**, **Mammoth Electronics**, and **Love My Switches** (Shopify public API — no key needed)
- Optional **Mouser** integration via free API key
- Save best prices linked to components; cheapest price shown in inventory list

### Platforms
- **macOS app** (SwiftUI, native) — primary interface
- **iOS / tvOS / watchOS** app targets included
- **Web UI** (React + TypeScript) — legacy browser interface
- **REST API** (FastAPI + SQLite) — backs the web UI

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Native app | Swift 6, SwiftUI, Swift Package Manager |
| REST API | Python 3.11, FastAPI, SQLAlchemy, SQLite |
| Web UI | React 19, TypeScript, Vite, Tailwind CSS |
| OCR analyzer | Python + Tesseract (`analyze_schematics.py`) |
| Supplier search | Shopify products.json + Mouser REST API |

---

## Project Structure

```
workshop/
├── native/              # SwiftUI app (macOS / iOS / tvOS / watchOS)
│   ├── Sources/WorkshopCore/   # Shared models, services, networking
│   ├── App/                    # Platform-specific app shells + shared views
│   ├── Package.swift
│   └── project.yml             # XcodeGen project spec
├── api/                 # FastAPI backend
│   ├── models/          # SQLAlchemy ORM models
│   ├── routers/         # API route handlers
│   ├── services/        # Build analyzer, BOM parser, schematic indexer
│   └── suppliers/       # Supplier adapter protocol + implementations
├── ui/                  # React web frontend
│   └── src/
│       ├── pages/
│       └── components/
├── scripts/             # CLI utilities
│   ├── analyze_schematics.py   # OCR + BOM extraction (Tesseract)
│   ├── seed_db.py
│   └── index_schematics.py
├── seeds/               # Seed data (components, suppliers)
├── Makefile
└── requirements.txt
```

---

## Getting Started

### Native macOS App

**Requirements:** Xcode 26+, XcodeGen

```bash
brew install xcodegen
cd native
xcodegen generate
open PedalWorkshop.xcodeproj
```

Build and run the `PedalWorkshop-macOS` scheme. The app is self-contained — it reads data from `~/Library/Application Support/PedalWorkshop/` and ships bundled seed data.

### Web / API (optional)

**Requirements:** Python 3.11+, Node 20+

```bash
make setup       # creates venv, installs deps, migrates DB, seeds data
make dev-api     # API on http://localhost:8000
make dev-ui      # Web UI on http://localhost:5173
```

### Schematic OCR Analysis

Point `analyze_schematics.py` at your schematic library to extract BOMs:

```bash
python3 scripts/analyze_schematics.py --workers 6
# Writes ~/Library/Application Support/PedalWorkshop/schematics_metadata.json
```

Requires: `tesseract`, `poppler` (for PDFs)

```bash
brew install tesseract poppler
```

---

## Contributing

This project is open to collaborators! Areas where help is especially welcome:

- **Supplier adapters** — DigiKey OAuth2, Small Bear (BigCommerce), Reverb
- **iOS / watchOS UI** — the native targets exist but views need polish for small screens
- **Schematic OCR** — improve the regex-based component extractor with ML
- **LibrePCB / KiCad integration** — parse native project files for BOM import
- **PCBWay quote API** — complete the PCB order integration
- **Jupyter notebook** — data analysis / inventory insights notebook

Please open an issue before starting large changes. PRs welcome.

---

## License

MIT — see `LICENSE` file.

---

*Built with [Claude Code](https://claude.ai/code)*
