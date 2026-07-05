# SPDX-License-Identifier: MIT
"""Dashboard view: stat cards + the three build-readiness tiers."""

import flet as ft

from ..build_analyzer import analyze, summary


def _stat_card(label, value, icon, color):
    return ft.Container(
        width=180,
        padding=16,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.08, color),
        content=ft.Column(
            spacing=4,
            controls=[
                ft.Row([ft.Icon(icon, color=color, size=20),
                        ft.Text(label, size=12, color=ft.Colors.ON_SURFACE_VARIANT)],
                       spacing=8),
                ft.Text(str(value), size=28, weight=ft.FontWeight.BOLD),
            ],
        ),
    )


def _tier_section(app, title, color, statuses):
    if not statuses:
        body = ft.Text("None", italic=True, color=ft.Colors.ON_SURFACE_VARIANT)
    else:
        rows = []
        for st in statuses:
            subtitle = st.effect_type or st.status
            missing_note = (
                "Ready" if st.missing_count == 0
                else "{} missing".format(st.missing_count)
            )
            rows.append(
                ft.ListTile(
                    title=ft.Text(st.project_name),
                    subtitle=ft.Text("{} • {} BOM rows".format(subtitle, st.bom_count)),
                    trailing=ft.Text(missing_note, color=color, weight=ft.FontWeight.W_600),
                    on_click=(lambda e, pid=st.project_id: app.navigate_to(2, project_id=pid)),
                )
            )
        body = ft.Column(rows, spacing=0, tight=True)

    return ft.Container(
        expand=1,
        padding=12,
        border_radius=12,
        border=ft.border.all(1, ft.Colors.with_opacity(0.3, color)),
        content=ft.Column(
            [
                ft.Row([ft.Container(width=10, height=10, bgcolor=color,
                                     border_radius=5),
                        ft.Text("{} ({})".format(title, len(statuses)),
                                weight=ft.FontWeight.BOLD, size=16)],
                       spacing=8),
                ft.Divider(height=8),
                body,
            ],
            spacing=6,
        ),
    )


def build(app):
    store = app.store
    components = store.list_components()
    projects = store.list_projects()
    bom_items = store.list_bom_items()

    tiers = analyze(projects, bom_items, components)
    s = summary(components, projects, tiers)

    stat_cards = ft.Row(
        wrap=True,
        spacing=12,
        run_spacing=12,
        controls=[
            _stat_card("Total parts", s.total_components, ft.Icons.WIDGETS, ft.Colors.AMBER),
            _stat_card("Unique parts", s.total_unique_parts, ft.Icons.CATEGORY, ft.Colors.BLUE),
            _stat_card("Projects", s.total_projects, ft.Icons.DEVELOPER_BOARD, ft.Colors.PURPLE),
            _stat_card("Active builds", s.active_builds, ft.Icons.BUILD, ft.Colors.TEAL),
            _stat_card("Low stock", s.low_stock_count, ft.Icons.WARNING_AMBER, ft.Colors.RED),
        ],
    )

    tier_row = ft.Row(
        [
            _tier_section(app, "Ready", ft.Colors.GREEN, tiers.ready),
            _tier_section(app, "ARNA 1-3", ft.Colors.AMBER, tiers.arna13),
            _tier_section(app, "ARNA 4+", ft.Colors.RED, tiers.arna4plus),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
        expand=True,
    )

    return ft.Column(
        [
            ft.Text("Dashboard", size=26, weight=ft.FontWeight.BOLD),
            stat_cards,
            ft.Container(height=8),
            ft.Text("Build readiness", size=18, weight=ft.FontWeight.W_600),
            tier_row,
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
