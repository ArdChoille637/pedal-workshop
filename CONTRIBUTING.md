# Contributing to Pedal Workshop

Thanks for your interest! This is a passion project built for boutique guitar pedal makers. All skill levels welcome — whether you know Swift, Python, or just pedals.

## Quick orientation

```
native/   SwiftUI app (macOS / iOS / tvOS / watchOS) — primary UI
api/      FastAPI backend + SQLAlchemy — backs the web interface
ui/       React web frontend
scripts/  CLI utilities (OCR analyzer, seeder, indexer)
```

The macOS native app is the most actively developed surface. The Python API exists as an alternative backend for the web UI.

## What needs help

| Area | Skills needed | Effort |
|------|--------------|--------|
| Supplier adapters (`api/suppliers/`) | Python, HTTP | Small–Medium |
| iOS / watchOS view polish | SwiftUI | Medium |
| DigiKey OAuth2 integration | Swift async, OAuth | Large |
| Schematic OCR improvement | Python, regex / ML | Medium–Large |
| LibrePCB / KiCad BOM import | Python, XML parsing | Medium |
| Unit tests — Swift (XCTest) | Swift | Small per file |
| Unit tests — Python (pytest) | Python | Small per file |
| Jupyter analysis notebook | Python, pandas | Small |

## Development setup

### Native app (macOS)
```bash
# Requirements: Xcode 26+, XcodeGen
brew install xcodegen
cd native
xcodegen generate
open PedalWorkshop.xcodeproj
# Select PedalWorkshop-macOS scheme → Run
```

### Python API + Web UI
```bash
# Requirements: Python 3.11+, Node 20+
make setup       # venv + deps + DB + seed
make dev-api     # http://localhost:8000
make dev-ui      # http://localhost:5173
```

### Schematic OCR
```bash
brew install tesseract poppler
python3 scripts/analyze_schematics.py --workers 6
```

## Making changes

1. **Fork** the repo and create a branch: `git checkout -b feature/my-thing`
2. **Keep commits small** and focused — one logical change per commit
3. **Add comments** explaining *why*, not just *what* — especially for non-obvious logic
4. **Test** your change manually before opening a PR
5. **Open a PR** against `main` with a clear description of what changed and why

## Adding a supplier adapter

The easiest contribution is implementing one of the stub adapters.

**Shopify stores** (Tayda, Mammoth, Love My Switches):
- See the detailed guide in `api/suppliers/tayda.py`
- On the Swift side, add a `ShopifySearcher` instance in `SupplierSearch.swift` — see the `// TO ADD A NEW SHOPIFY SUPPLIER` comment block

**Non-Shopify stores** (Mouser REST API, DigiKey OAuth2):
- See `api/suppliers/base.py` for the `SupplierAdapter` protocol
- See `// TO ADD A NON-SHOPIFY SUPPLIER` in `SupplierSearch.swift`

## Code style

**Swift:** Follow Swift API Design Guidelines. Use `// MARK: –` sections. Add triple-slash docs to all `public` symbols. Run `swift format` if available.

**Python:** Follow PEP 8. Use type hints everywhere. Docstrings in NumPy style (see existing files). Run `ruff check .` before committing.

**Both:** Add the SPDX header to new files:
```
// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop
```

## Commit messages

Use the imperative mood and keep the first line under 72 characters:
```
Add DigiKey OAuth2 token refresh

Implements the OAuth2 PKCE flow for DigiKey API v3. Tokens are stored
in the Keychain via KeychainHelper. Refresh is automatic on 401.
```

## Questions?

Open a GitHub Discussion — no question is too basic.
