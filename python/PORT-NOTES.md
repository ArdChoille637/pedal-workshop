# Pedal Workshop — Flet (Python) port notes

A desktop port of the native macOS Pedal Workshop app, built with
[Flet](https://flet.dev). Full feature parity with the shared spec
(`../android/SPEC.md`): Dashboard, Inventory, Projects + BOMs, the Build
Analyzer, Suppliers, Price Lookup (Mouser), Schematics browser, and Settings.
No AI/LLM anywhere; reads only local/bundled data plus the Mouser REST API.

## Run it

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py            # native desktop window
```

To run in a browser instead (useful for headless/smoke checks):

```bash
.venv/bin/python -c "import flet as ft; from pedalworkshop.app import main; \
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550)"
```

First launch seeds `components`, `suppliers`, `projects`, and `bom_items` from
`pedalworkshop/seeds/` into `~/.pedalworkshop/` (shown in Settings).

## Flet version

Developed and verified against **flet 0.85.3** (Python 3.11), pinned
`flet>=0.85,<0.86` in `requirements.txt`. This is a post-0.80 Flet, whose API
differs from the older tutorials in a few places. The port adapts to the
installed version:

| Concern | Old Flet | Flet 0.85 (what this port uses) |
|---|---|---|
| Dialogs | `page.open(dlg)` / `page.close(dlg)` | `page.show_dialog(dlg)` / `page.pop_dialog()` |
| SnackBar | `page.open(snack)` | `page.show_dialog(snack)` (SnackBar is a `DialogControl`) |
| FilePicker | overlay control + `on_result` event | `page.services` service; **async** `await fp.get_directory_path(...)` returns the path directly |
| Dropdown change event | `on_change=` | `on_select=` |
| Image fit | `ft.ImageFit.*` | `ft.BoxFit.*` |
| Layout helpers | `ft.border.all(...)`, `ft.padding.symmetric(...)`, `ft.alignment.center` | classmethods `ft.Border.all(...)`, `ft.Padding.symmetric(...)`, `ft.Alignment(x, y)` |
| Launch | `ft.app(target=main)` | `ft.run(main)` (`ft.app` still works, deprecated) |

Two of these are handled centrally so the view code stays readable and the
reference `dashboard.py` runs unmodified:

- **Layout-helper shim** — `views/_ui.py::_install_layout_compat()` re-attaches
  `ft.border.all`, `ft.padding.{all,symmetric,only}`, and `ft.alignment.*`
  presets by forwarding to the new classmethods. It is installed at import time
  from `views/__init__.py`, so it is active before any `build()` runs. It is a
  no-op on a Flet that still has the old helpers.
- **Dialog / FilePicker wrappers** — `views/_ui.py` provides
  `open_dialog` / `close_dialog` / `pick_directory` (and `snack`) that select
  the right API and fall back to the older forms if run on an older Flet.

`main.py` uses `ft.app(target=main)` exactly as the spec asks; on 0.85 that is a
thin (deprecated) wrapper over `ft.run()` and launches cleanly. The only console
output is a one-line `DeprecationWarning`.

## Files added by this port

- `main.py` — entry point.
- `pedalworkshop/views/_ui.py` — shared dialog/FilePicker/compat helpers.
- `pedalworkshop/views/inventory.py`
- `pedalworkshop/views/projects.py`
- `pedalworkshop/views/suppliers.py`
- `pedalworkshop/views/price_lookup.py`
- `pedalworkshop/views/schematics.py`
- `pedalworkshop/views/settings.py`
- `requirements.txt`, `PORT-NOTES.md`

(The core — `models.py`, `storage.py`, `build_analyzer.py`, `supplier_search.py`,
`app.py`, `views/dashboard.py` — was pre-existing and left unchanged, except the
`views/__init__.py` gained one line to install the layout-compat shim.)

## Secure key storage

The Mouser API key is stored via the OS keyring when the `keyring` package is
importable, otherwise it falls back to `settings.json` (plaintext). Settings
shows which backend is active (`Store.key_storage_backend()`). `keyring` is an
optional dependency; if it is not installed the app still works via the fallback.

## Verification performed

- **Parse**: `ast.parse` over every `.py` — OK.
- **Import**: `pedalworkshop.app`, all seven view modules, `_ui`, and `main` —
  OK; each view exposes `build(app)`.
- **Unit tests**: `pytest -q` → **15 passed** (all `build_analyzer` tests).
- **View construction**: every `build(app)` and every dialog constructor
  (add/edit/delete component, new/delete project, add/edit/delete BOM item,
  schematic image + PDF detail) built against a real seeded `Store` through the
  actual Flet control constructors — OK.
- **Smoke launch**: `ft.app(target=main, view=WEB_BROWSER)` served HTTP 200 with
  no tracebacks (debug logging on); websocket endpoint healthy.

## Stubs / caveats

- **Schematics grid is virtualized.** The thumbnail grid is an `ft.GridView`
  (`build_controls_on_demand=True`, `cache_extent=600`), which wraps Flutter's
  `GridView.builder`: it builds/renders only the tiles in and near the viewport
  and recycles them as you scroll, so a folder of hundreds/thousands of files
  renders instantly and never eager-loads every image. Building the view for an
  881-file folder takes ~0.1s. The category filter rebuilds the tile list from
  the filtered set; the GridView still only renders visible cells.
- **PDF preview** shows a document icon + an "Open PDF" button
  (`page.launch_url("file://…")`) rather than rendering page 1 inline. The spec
  allows either ("render page 1 or offer 'open'"); inline PDF rasterisation
  would need an extra dependency (e.g. pdf2image/poppler), intentionally avoided
  to keep the app dependency-light. Image schematics render inline.
- **Price Lookup** runs the Mouser HTTP call on a background thread
  (`page.run_thread`) with a ProgressRing; results appear when it completes. It
  requires a Mouser key (free at mouser.com/api-hub) set in Settings.
- Local image/PDF `file://` opening depends on the OS default handler; on the
  desktop (FLET_APP) view this uses the system browser/viewer.
