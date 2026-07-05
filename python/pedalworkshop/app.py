# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Flet UI entry point for Pedal Workshop.

Builds a NavigationRail shell with: Dashboard, Inventory, Projects, Suppliers,
Price Lookup, Schematics, Settings. Each destination is rendered by a builder
function in pedalworkshop/views/.
"""

import flet as ft

from .storage import Store
from .views import (
    dashboard as dashboard_view,
    inventory as inventory_view,
    projects as projects_view,
    suppliers as suppliers_view,
    price_lookup as price_lookup_view,
    schematics as schematics_view,
    settings as settings_view,
)

# NavigationRail destinations, in order.
_DESTINATIONS = [
    ("Dashboard", ft.Icons.DASHBOARD_OUTLINED, ft.Icons.DASHBOARD),
    ("Inventory", ft.Icons.INVENTORY_2_OUTLINED, ft.Icons.INVENTORY_2),
    ("Projects", ft.Icons.DEVELOPER_BOARD_OUTLINED, ft.Icons.DEVELOPER_BOARD),
    ("Suppliers", ft.Icons.STORE_OUTLINED, ft.Icons.STORE),
    ("Price Lookup", ft.Icons.SEARCH_OUTLINED, ft.Icons.SEARCH),
    ("Schematics", ft.Icons.IMAGE_OUTLINED, ft.Icons.IMAGE),
    ("Settings", ft.Icons.SETTINGS_OUTLINED, ft.Icons.SETTINGS),
]


class WorkshopApp:
    """Holds shared UI state (the Store, the current view, cross-view nav)."""

    def __init__(self, page: ft.Page, store: Store):
        self.page = page
        self.store = store
        # A project id to auto-open when switching to the Projects view (set by
        # dashboard tier taps).
        self.pending_project_id = None
        self.content = ft.Container(expand=True, padding=20)

        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=88,
            min_extended_width=160,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=unsel, selected_icon=sel, label=label
                )
                for (label, unsel, sel) in _DESTINATIONS
            ],
            on_change=self._on_rail_change,
        )

    # ------------------------------------------------------------------ nav
    def _on_rail_change(self, e):
        self.render()

    def navigate_to(self, index: int, project_id=None):
        """Programmatic navigation (e.g. dashboard -> a project's detail)."""
        self.pending_project_id = project_id
        self.rail.selected_index = index
        self.render()

    def render(self):
        idx = self.rail.selected_index or 0
        builders = [
            lambda: dashboard_view.build(self),
            lambda: inventory_view.build(self),
            lambda: projects_view.build(self),
            lambda: suppliers_view.build(self),
            lambda: price_lookup_view.build(self),
            lambda: schematics_view.build(self),
            lambda: settings_view.build(self),
        ]
        try:
            self.content.content = builders[idx]()
        except Exception as exc:  # keep the shell alive on a view error
            self.content.content = ft.Text("View error: {}".format(exc),
                                           color=ft.Colors.RED)
        self.page.update()

    def build(self):
        return ft.Row(
            [
                self.rail,
                ft.VerticalDivider(width=1),
                self.content,
            ],
            expand=True,
        )


def main(page: ft.Page):
    page.title = "Pedal Workshop"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)
    page.window_width = 1180
    page.window_height = 820
    page.padding = 0

    store = Store()
    app = WorkshopApp(page, store)
    page.add(app.build())
    app.render()
