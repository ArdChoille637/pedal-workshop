# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Suppliers view: read-only list of reference suppliers.

Only Mouser is a live search backend (see supplier_search.py); the Shopify
stores are reference-only. That caveat is shown in the caption.
"""

import flet as ft


def _api_badge(api_type):
    live = (api_type or "").strip().lower() == "mouser"
    color = ft.Colors.GREEN if live else ft.Colors.ON_SURFACE_VARIANT
    label = "live search" if live else (api_type or "manual")
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.14, color),
        content=ft.Text(label, size=11, color=color, weight=ft.FontWeight.W_600),
    )


def build(app):
    store = app.store
    suppliers = store.list_suppliers()
    page = app.page

    rows = []
    for s in suppliers:
        website = (s.website or "").strip()
        subtitle_bits = []
        if website:
            subtitle_bits.append(website)
        subtitle = "  •  ".join(subtitle_bits) if subtitle_bits else "no website on file"

        trailing_controls = [_api_badge(s.api_type)]
        if website:
            trailing_controls.append(
                ft.IconButton(
                    icon=ft.Icons.OPEN_IN_NEW,
                    tooltip="Open website",
                    on_click=(lambda e, url=website: page.launch_url(url)),
                )
            )

        rows.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.STORE_OUTLINED),
                title=ft.Text(s.name, weight=ft.FontWeight.W_600),
                subtitle=ft.Text(subtitle, color=ft.Colors.ON_SURFACE_VARIANT),
                trailing=ft.Row(trailing_controls, spacing=4, tight=True),
            )
        )

    if not rows:
        body = ft.Text("No suppliers.", italic=True,
                       color=ft.Colors.ON_SURFACE_VARIANT)
    else:
        body = ft.Column(rows, spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.Column(
        [
            ft.Text("Suppliers", size=26, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Reference suppliers. Only Mouser is a live search backend "
                "(Price Lookup); the others block their public endpoints and are "
                "listed for reference only.",
                size=13, color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Divider(height=12),
            body,
        ],
        spacing=10,
        expand=True,
    )
