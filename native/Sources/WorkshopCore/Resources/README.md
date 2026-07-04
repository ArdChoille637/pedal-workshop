<!-- SPDX-License-Identifier: MIT -->
# Bundled seed data

These JSON files are the app's **first-run seeds**, copied into
`~/Library/Application Support/PedalWorkshop/` the first time the app launches.
At runtime the app reads from Application Support, not from this bundle.

| file | contents | published? |
|---|---|---|
| `components.json` | generic default component list | ✅ generic |
| `suppliers.json` | supplier definitions | ✅ generic |
| `projects.json` | sample project(s) | ✅ sample |
| `schematics.json` | schematic index | **ships empty `[]`** |
| `schematics_metadata.json` | OCR'd BOM metadata | **ships empty `[]`** |

`schematics.json` and `schematics_metadata.json` ship **empty** on purpose: a
real index would embed absolute home paths and OCR'd text from copyrighted
schematics. Populate them locally against **your own** schematic library with
the app's **Settings → Rescan Schematics Folder**, or:

```sh
python3 pipeline/tools/generate_native_index.py   # → schematics.json
python3 pipeline/tools/analyze_schematics.py       # → schematics_metadata.json
```
