# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Settings view: Mouser API key, schematics folder, and the data directory.

The Mouser key is stored via the Store's secure path (OS keyring if available,
else settings.json -- the backend is displayed so the user knows which).
"""

import flet as ft

from . import _ui


def build(app):
    store = app.store
    page = app.page

    # ---- Mouser API key ------------------------------------------------
    key_field = ft.TextField(
        label="Mouser API key",
        value=store.get_mouser_key() or "",
        password=True,
        can_reveal_password=True,
        hint_text="Paste your Mouser Search API key",
        dense=True,
        width=460,
    )
    backend_note = ft.Text(
        "Stored in: {}".format(store.key_storage_backend()),
        size=12, color=ft.Colors.ON_SURFACE_VARIANT,
    )

    def save_key(e):
        store.set_mouser_key(key_field.value or "")
        # Reflect any normalisation and refresh the backend note.
        key_field.value = store.get_mouser_key() or ""
        backend_note.value = "Stored in: {}".format(store.key_storage_backend())
        _ui.snack(page, "Mouser API key saved.")
        page.update()

    def clear_key(e):
        store.set_mouser_key("")
        key_field.value = ""
        _ui.snack(page, "Mouser API key cleared.")
        page.update()

    key_card = ft.Container(
        padding=16, border_radius=12,
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE)),
        content=ft.Column(
            [
                ft.Text("Mouser API", size=16, weight=ft.FontWeight.W_600),
                ft.Text("Free at mouser.com/api-hub. Required for Price Lookup.",
                        size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                key_field,
                ft.Row([
                    ft.FilledButton("Save key", icon=ft.Icons.SAVE, on_click=save_key),
                    ft.TextButton("Clear", on_click=clear_key),
                    ft.TextButton(
                        "Get a key",
                        icon=ft.Icons.OPEN_IN_NEW,
                        on_click=lambda e: page.launch_url("https://www.mouser.com/api-hub/"),
                    ),
                ], spacing=8),
                backend_note,
            ],
            spacing=8,
        ),
    )

    # ---- Schematics folder --------------------------------------------
    current_folder = store.get_setting("schematics_folder") or ""
    folder_text = ft.Text(
        current_folder or "No folder chosen yet.",
        size=13,
        color=(ft.Colors.ON_SURFACE if current_folder else ft.Colors.ON_SURFACE_VARIANT),
        selectable=True,
    )
    indexed_count = ft.Text(
        "{} schematic file(s) indexed.".format(len(store.list_schematics())),
        size=12, color=ft.Colors.ON_SURFACE_VARIANT,
    )

    def on_folder_picked(path):
        if not path:
            return
        store.set_setting("schematics_folder", path)
        found = store.index_schematics_folder(path)
        folder_text.value = path
        indexed_count.value = "{} schematic file(s) indexed.".format(len(found))
        _ui.snack(page, "Indexed {} file(s).".format(len(found)))
        page.update()

    def choose_folder(e):
        _ui.pick_directory(page, on_folder_picked, "Choose schematics folder")

    folder_card = ft.Container(
        padding=16, border_radius=12,
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE)),
        content=ft.Column(
            [
                ft.Text("Schematics folder", size=16, weight=ft.FontWeight.W_600),
                ft.Text("Index .gif/.png/.jpg/.jpeg/.pdf files for the Schematics browser.",
                        size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                folder_text,
                indexed_count,
                ft.Row([
                    ft.FilledButton("Choose folder…", icon=ft.Icons.FOLDER_OPEN,
                                    on_click=choose_folder),
                ], spacing=8),
            ],
            spacing=8,
        ),
    )

    # ---- Data directory (read-only) -----------------------------------
    data_card = ft.Container(
        padding=16, border_radius=12,
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE)),
        content=ft.Column(
            [
                ft.Text("Data directory", size=16, weight=ft.FontWeight.W_600),
                ft.Text("Where inventory, projects, and settings are stored.",
                        size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(str(store.data_dir), size=13, selectable=True),
            ],
            spacing=8,
        ),
    )

    return ft.Column(
        [
            ft.Text("Settings", size=26, weight=ft.FontWeight.BOLD),
            key_card,
            folder_card,
            data_card,
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
