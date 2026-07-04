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

`schematics.json` ships **empty** on purpose: a real index would embed absolute
home paths and copyrighted schematic filenames. Populate it locally against
**your own** schematic library:

```sh
python3 pipeline/tools/generate_native_index.py   # → schematics.json (the index)
python3 pipeline/tools/package_schematics.py       # → Schematics/ (the files)
```

`Schematics/` holds the schematic image/PDF files packaged into the app bundle
(`.copy` in Package.swift). The app reads them from here — never from
`~/Documents` — so it never triggers the macOS Documents-folder permission
prompt. The files are gitignored (copyrighted + large); only `.gitkeep` is
committed, so a fresh clone builds an app with an empty schematic library.
