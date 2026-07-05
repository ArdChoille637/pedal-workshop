# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Price Lookup view: keyword search against Mouser (the only live backend).

The search itself is a blocking HTTP request; we run it on a background thread
via ``page.run_thread`` so the UI stays responsive and a ProgressRing shows
while it runs. State (query text, last results/failures, searching flag) lives
on the app so the view survives app.render() rebuilds.
"""

import flet as ft

from ..supplier_search import search_all
from . import _ui


def _state(app):
    st = getattr(app, "_price_state", None)
    if st is None:
        st = {"query": "", "results": None, "failures": [], "searching": False}
        app._price_state = st  # type: ignore[attr-defined]
    return st


def _run_search(app):
    """Kick off a Mouser search on a background thread."""
    st = _state(app)
    query = (st["query"] or "").strip()
    if not query or st["searching"]:
        return
    st["searching"] = True
    st["results"] = None
    st["failures"] = []
    app.render()

    store = app.store
    key = store.get_mouser_key() or ""

    def worker():
        try:
            results, failures = search_all(query, key)
        except Exception as exc:  # defensive: never let the thread die silently
            results, failures = [], ["Search failed ({}).".format(exc)]
        st["results"] = results
        st["failures"] = failures
        st["searching"] = False
        # Re-render on the UI thread.
        app.render()

    runner = getattr(app.page, "run_thread", None)
    if callable(runner):
        runner(worker)
    else:  # no threadpool available -> run inline (brief block).
        worker()


def _result_card(app, r):
    page = app.page
    dot_color = ft.Colors.GREEN if r.in_stock else ft.Colors.ON_SURFACE_VARIANT
    stock_label = "In stock" if r.in_stock else "Check availability"
    price_label = "${:.2f}".format(r.price) if r.price else "—"

    trailing = [
        ft.Column(
            [ft.Text(price_label, weight=ft.FontWeight.BOLD, size=16),
             ft.Row([ft.Container(width=8, height=8, border_radius=4, bgcolor=dot_color),
                     ft.Text(stock_label, size=11, color=ft.Colors.ON_SURFACE_VARIANT)],
                    spacing=4, tight=True)],
            horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2, tight=True,
        ),
    ]
    if r.url:
        trailing.append(
            ft.IconButton(ft.Icons.OPEN_IN_NEW, tooltip="Open on Mouser",
                          on_click=(lambda e, url=r.url: page.launch_url(url)))
        )

    return ft.Container(
        padding=12, border_radius=10,
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE)),
        content=ft.Row(
            [
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        [
                            ft.Text(r.title or r.sku, weight=ft.FontWeight.W_600, size=14),
                            ft.Text("{}  •  {}".format(r.supplier_name, r.sku),
                                    size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        spacing=2, tight=True,
                    ),
                ),
                ft.Row(trailing, spacing=8, tight=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _no_key_hint(app):
    return ft.Container(
        padding=16, border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.AMBER),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.KEY_OUTLINED, color=ft.Colors.AMBER),
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        [ft.Text("No Mouser API key set.", weight=ft.FontWeight.W_600),
                         ft.Text("Price Lookup needs a Mouser key. It's free at "
                                 "mouser.com/api-hub -- add it in Settings.",
                                 size=12, color=ft.Colors.ON_SURFACE_VARIANT)],
                        spacing=2, tight=True,
                    ),
                ),
                ft.FilledButton("Open Settings", icon=ft.Icons.SETTINGS,
                                on_click=lambda e: app.navigate_to(6)),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
        ),
    )


def build(app):
    store = app.store
    page = app.page
    st = _state(app)
    has_key = bool(store.get_mouser_key())

    def on_query(e):
        st["query"] = e.control.value or ""

    def do_search(e):
        _run_search(app)

    query_field = ft.TextField(
        label="Search Mouser", value=st["query"], expand=True, dense=True,
        prefix_icon=ft.Icons.SEARCH, on_change=on_query, on_submit=do_search,
        hint_text="e.g. TL072, 1n4148, 10k resistor",
    )
    search_btn = ft.FilledButton("Search", icon=ft.Icons.SEARCH, on_click=do_search,
                                 disabled=st["searching"])

    controls = [
        ft.Text("Price Lookup", size=26, weight=ft.FontWeight.BOLD),
        ft.Text("Live keyword search against Mouser.",
                size=13, color=ft.Colors.ON_SURFACE_VARIANT),
    ]

    if not has_key:
        controls.append(_no_key_hint(app))

    controls.append(
        ft.Row([query_field, search_btn], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.CENTER)
    )

    # --- results / status area ---
    if st["searching"]:
        controls.append(
            ft.Row([ft.ProgressRing(width=20, height=20),
                    ft.Text("Searching Mouser…", color=ft.Colors.ON_SURFACE_VARIANT)],
                   spacing=10)
        )
    else:
        for note in st["failures"]:
            controls.append(
                ft.Container(
                    padding=10, border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.RED),
                    content=ft.Row([ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED,
                                            size=18),
                                    ft.Text(note, size=12, color=ft.Colors.RED)],
                                   spacing=8),
                )
            )
        results = st["results"]
        if results is not None:
            if results:
                controls.append(ft.Text("{} result(s)".format(len(results)),
                                        size=12, color=ft.Colors.ON_SURFACE_VARIANT))
                controls.append(
                    ft.Column([_result_card(app, r) for r in results],
                              spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
                )
            elif not st["failures"]:
                controls.append(
                    ft.Text("No results.", italic=True,
                            color=ft.Colors.ON_SURFACE_VARIANT)
                )

    return ft.Column(controls, spacing=12, expand=True)
