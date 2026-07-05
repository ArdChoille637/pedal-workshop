# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Schematics view: a thumbnail grid of indexed image/PDF files.

Empty state offers a folder chooser (FilePicker.get_directory_path) that indexes
the folder into the schematics collection. Image files show an inline thumbnail;
PDFs show a document icon. Clicking a card opens a detail dialog with the larger
image, or an "Open" button (page.launch_url) for PDFs.
"""

import flet as ft

from . import _ui

_IMAGE_TYPES = {"png", "jpg", "jpeg", "gif"}


def _state(app):
    st = getattr(app, "_schem_state", None)
    if st is None:
        st = {"category": "All"}
        app._schem_state = st  # type: ignore[attr-defined]
    return st


def _index_folder(app, path):
    if not path:
        return
    store = app.store
    store.set_setting("schematics_folder", path)
    store.index_schematics_folder(path)
    _ui.snack(app.page, "Indexed schematics folder.")
    app.render()


def _choose_folder(app):
    _ui.pick_directory(app.page, lambda p: _index_folder(app, p),
                       "Choose schematics folder")


def _empty_state(app):
    return ft.Container(
        expand=True, alignment=ft.alignment.center,
        content=ft.Column(
            [
                ft.Icon(ft.Icons.IMAGE_OUTLINED, size=64,
                        color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text("No schematics indexed yet.", size=16),
                ft.Text("Choose a folder of .gif/.png/.jpg/.jpeg/.pdf files to browse them.",
                        size=13, color=ft.Colors.ON_SURFACE_VARIANT,
                        text_align=ft.TextAlign.CENTER),
                ft.FilledButton("Choose folder…", icon=ft.Icons.FOLDER_OPEN,
                                on_click=lambda e: _choose_folder(app)),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12,
        ),
    )


def _detail_dialog(app, schem):
    page = app.page
    is_image = (schem.file_type or "").lower() in _IMAGE_TYPES

    if is_image:
        preview = ft.Image(src=schem.file_path, fit=ft.BoxFit.CONTAIN,
                           width=560, height=420,
                           error_content=ft.Text("Could not load image."))
    else:
        preview = ft.Container(
            width=560, height=200, alignment=ft.alignment.center,
            content=ft.Column(
                [ft.Icon(ft.Icons.PICTURE_AS_PDF, size=64, color=ft.Colors.RED_300),
                 ft.Text("PDF document", color=ft.Colors.ON_SURFACE_VARIANT)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
            ),
        )

    meta = ft.Text(
        "{}  •  {}".format(schem.category_folder or "uncategorised",
                           (schem.file_type or "").upper()),
        size=12, color=ft.Colors.ON_SURFACE_VARIANT,
    )

    actions = [ft.TextButton("Close", on_click=lambda e: _ui.close_dialog(page, dlg))]
    if not is_image:
        actions.insert(0, ft.FilledButton(
            "Open PDF", icon=ft.Icons.OPEN_IN_NEW,
            on_click=lambda e: page.launch_url("file://" + schem.file_path)))
    else:
        actions.insert(0, ft.TextButton(
            "Open externally", icon=ft.Icons.OPEN_IN_NEW,
            on_click=lambda e: page.launch_url("file://" + schem.file_path)))

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(schem.file_name),
        content=ft.Container(width=580,
                             content=ft.Column([meta, preview], spacing=10, tight=True,
                                               scroll=ft.ScrollMode.AUTO)),
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def _card(app, schem):
    """One GridView tile. Sized by the GridView (max_extent/child_aspect_ratio),
    so the card and thumbnail use ``expand`` rather than fixed dimensions.

    The ``ft.Image`` here is a lightweight control object; the actual bytes are
    only fetched/decoded client-side when GridView renders this tile (it builds
    controls on demand and virtualizes off-screen cells), so a folder of
    hundreds of images never eager-loads.
    """
    is_image = (schem.file_type or "").lower() in _IMAGE_TYPES
    if is_image:
        thumb = ft.Image(src=schem.file_path, fit=ft.BoxFit.COVER, expand=True,
                         error_content=ft.Container(
                             alignment=ft.alignment.center,
                             content=ft.Icon(ft.Icons.BROKEN_IMAGE_OUTLINED,
                                             color=ft.Colors.ON_SURFACE_VARIANT)))
    else:
        thumb = ft.Container(
            expand=True, alignment=ft.alignment.center,
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
            content=ft.Icon(ft.Icons.PICTURE_AS_PDF, size=48, color=ft.Colors.RED_300),
        )

    return ft.Container(
        border_radius=10,
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE)),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        ink=True,
        on_click=lambda e, s=schem: _ui.open_dialog(app.page, _detail_dialog(app, s)),
        content=ft.Column(
            [
                ft.Container(expand=True, content=thumb),  # thumbnail fills the tile
                ft.Container(
                    padding=8,
                    content=ft.Column(
                        [
                            ft.Text(schem.file_name, size=12, weight=ft.FontWeight.W_600,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(schem.category_folder or "uncategorised", size=11,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=2, tight=True,
                    ),
                ),
            ],
            spacing=0, tight=True,
        ),
    )


def build(app):
    store = app.store
    st = _state(app)
    schematics = store.list_schematics()

    if not schematics:
        return ft.Column(
            [
                ft.Text("Schematics", size=26, weight=ft.FontWeight.BOLD),
                _empty_state(app),
            ],
            spacing=12, expand=True,
        )

    # Category filter.
    cats = sorted({s.category_folder for s in schematics if s.category_folder})
    categories = ["All"] + cats
    if st["category"] not in categories:
        st["category"] = "All"

    def on_category(e):
        st["category"] = e.control.value or "All"
        app.render()

    visible = [s for s in schematics
               if st["category"] == "All" or s.category_folder == st["category"]]

    cat_dd = ft.Dropdown(
        label="Category", value=st["category"], dense=True, width=220,
        options=[ft.DropdownOption(key=c, text=c) for c in categories],
        on_select=on_category,
    )
    reindex_btn = ft.OutlinedButton("Re-index folder…", icon=ft.Icons.FOLDER_OPEN,
                                    on_click=lambda e: _choose_folder(app))

    # Virtualized thumbnail grid. ft.GridView wraps Flutter's GridView.builder:
    # with build_controls_on_demand it only builds/renders the cells in (and
    # near) the viewport and recycles them as the user scrolls, so indexing a
    # folder of hundreds/thousands of files renders instantly and never
    # eager-loads every image. cache_extent adds a modest overscan (~one extra
    # viewport-worth of rows) so scrolling stays smooth without pre-loading all.
    #
    # max_extent caps each tile's main-axis size (Flutter picks the column count
    # so tiles are <= this wide); child_aspect_ratio < 1 makes tiles taller than
    # wide, leaving room for the thumbnail plus the two caption lines.
    grid = ft.GridView(
        controls=[_card(app, s) for s in visible],
        max_extent=200,
        child_aspect_ratio=0.82,
        spacing=12,
        run_spacing=12,
        build_controls_on_demand=True,
        cache_extent=600,
        padding=ft.padding.only(right=6),
        expand=True,
    )

    return ft.Column(
        [
            ft.Row([ft.Text("Schematics", size=26, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.Text("{} file(s)".format(len(visible)), size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT)],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([cat_dd, reindex_btn], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(height=10),
            grid,  # GridView scrolls itself; no outer scrolling wrapper.
        ],
        spacing=12, expand=True,
    )
