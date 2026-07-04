# Contributing to Pedal Workshop

Thanks for your interest! This is a passion project for guitar-pedal builders.
All skill levels welcome — Swift, Python, or just pedals.

## Orientation

```
native/    the macOS app (SwiftUI) + WorkshopCore Swift package — the product
pipeline/  optional offline schematic→KiCad batch tooling (Python)
seeds/     generic default data
```

The **macOS app is the product** and contains no AI/LLM code — it reads static
JSON only. The **pipeline** is separate offline tooling; it is never invoked by
the app. Please keep that boundary intact.

## What needs help

| Area | Skills | Effort |
|---|---|---|
| WorkshopCore unit tests (XCTest) | Swift | Small per file |
| Split large views / view polish | SwiftUI | Medium |
| Supplier searchers in `SupplierSearch.swift` | Swift async, HTTP | Small–Medium |
| Pipeline: KiCad netlist quality | Python, KiCad | Medium |
| Pipeline: OCR / extraction accuracy | Python | Medium |

## Development setup

### Native app (macOS 26+, Xcode 26+)
```sh
brew install xcodegen
cd native && ./launch.sh      # generates project, builds, installs, launches
```

### Pipeline (optional)
```sh
cd pipeline
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
brew install tesseract poppler kicad
```

## Making changes

1. **Fork** and branch: `git checkout -b feature/my-thing`
2. **Small, focused commits** — one logical change each
3. **Comment the _why_**, not the _what_
4. **Build/test** before opening a PR (`cd native && ./launch.sh`)
5. **Open a PR** against `main` with a clear description

## Code style

- **Swift:** Swift API Design Guidelines, `// MARK:` sections, triple-slash docs
  on `public` symbols.
- **Python:** PEP 8, type hints, docstrings. `ruff check .` before committing.
- **New files** get the SPDX header:
  ```
  // SPDX-License-Identifier: MIT
  // Copyright (c) 2026 Pedal Workshop Contributors
  // https://github.com/ArdChoille637/pedal-workshop
  ```

## Commit messages

Imperative mood, first line under 72 chars, explain the _why_ in the body.

## Questions?

Open a GitHub Discussion — no question is too basic.
