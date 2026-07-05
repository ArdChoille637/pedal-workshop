# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Projects view: master list + a detail panel.

The detail panel shows the selected project's readiness tier and missing parts
(computed by build_analyzer.analyze on just that project) and its BOM items,
with add/edit/delete for BOM rows and a "New project" dialog.

The selected project id is tracked on the app. Arriving from the dashboard sets
``app.pending_project_id``, which we consume once to auto-open that project.
"""

import flet as ft

from ..models import Project, BOMItem
from ..build_analyzer import analyze
from . import _ui

_STATUSES = ["design", "prototype", "production"]

_TIER_META = {
    "ready": ("Ready to build", ft.Colors.GREEN),
    "arna13": ("ARNA 1-3", ft.Colors.AMBER),
    "arna4plus": ("ARNA 4+", ft.Colors.RED),
}


def _selected_id(app):
    """Resolve the currently-selected project id, consuming pending nav once."""
    if getattr(app, "pending_project_id", None) is not None:
        app._proj_selected = app.pending_project_id  # type: ignore[attr-defined]
        app.pending_project_id = None
    return getattr(app, "_proj_selected", None)


def _select(app, pid):
    app._proj_selected = pid  # type: ignore[attr-defined]
    app.render()


def _status_for_project(app, project):
    """Return (tier_key, ProjectBuildStatus|None) for a single project."""
    store = app.store
    bom = store.list_bom_items(project_id=project.id)
    components = store.list_components()
    tiers = analyze([project], bom, components)
    if tiers.ready:
        return "ready", tiers.ready[0]
    if tiers.arna13:
        return "arna13", tiers.arna13[0]
    if tiers.arna4plus:
        return "arna4plus", tiers.arna4plus[0]
    return None, None  # no BOM rows


# =====================================================================
# Dialogs
# =====================================================================
def _project_dialog(app):
    store = app.store
    page = app.page

    f_name = ft.TextField(label="Name *", dense=True, width=360)
    f_type = ft.TextField(label="Effect type", dense=True, width=360,
                          hint_text="e.g. overdrive, fuzz, delay")
    f_status = ft.Dropdown(
        label="Status", value="design", dense=True, width=200,
        options=[ft.DropdownOption(key=s, text=s) for s in _STATUSES],
    )
    f_desc = ft.TextField(label="Description", dense=True, width=360,
                          multiline=True, min_lines=1, max_lines=3)
    error = ft.Text("", color=ft.Colors.RED, size=12)

    def save(e):
        name = (f_name.value or "").strip()
        if not name:
            error.value = "Name is required."
            page.update()
            return
        created = store.add_project(Project(
            id=0, name=name, slug="",
            status=f_status.value or "design",
            effect_type=(f_type.value or "").strip() or None,
            description=(f_desc.value or "").strip() or None,
        ))
        _ui.close_dialog(page, dlg)
        _select(app, created.id)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("New project"),
        content=ft.Container(
            width=400,
            content=ft.Column([f_name, f_type, f_status, f_desc, error],
                              spacing=10, tight=True),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: _ui.close_dialog(page, dlg)),
            ft.FilledButton("Create", on_click=save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def _delete_project_dialog(app, project):
    page = app.page
    store = app.store

    def do_delete(e):
        store.delete_project(project.id)
        _ui.close_dialog(page, dlg)
        if getattr(app, "_proj_selected", None) == project.id:
            app._proj_selected = None  # type: ignore[attr-defined]
        app.render()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Delete project?"),
        content=ft.Text("Delete '{}' and all its BOM items? This cannot be undone."
                        .format(project.name)),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: _ui.close_dialog(page, dlg)),
            ft.FilledButton("Delete", on_click=do_delete,
                            style=ft.ButtonStyle(bgcolor=ft.Colors.RED)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def _bom_dialog(app, project, existing=None):
    store = app.store
    page = app.page
    is_edit = existing is not None

    f_ref = ft.TextField(label="Reference", dense=True, width=160,
                         value=(existing.reference or "" if is_edit else ""),
                         hint_text="e.g. R1")
    f_cat = ft.TextField(label="Category *", dense=True, width=200,
                         value=(existing.category if is_edit else ""),
                         hint_text="e.g. resistor")
    f_val = ft.TextField(label="Value *", dense=True, width=200,
                         value=(existing.value if is_edit else ""),
                         hint_text="e.g. 10k")
    f_qty = ft.TextField(label="Quantity", dense=True, width=120,
                         value=str(existing.quantity if is_edit else 1),
                         keyboard_type=ft.KeyboardType.NUMBER)
    f_opt = ft.Switch(label="Optional",
                      value=bool(existing.is_optional) if is_edit else False)
    error = ft.Text("", color=ft.Colors.RED, size=12)

    def _qty():
        try:
            return max(1, int(str(f_qty.value).strip() or 1))
        except ValueError:
            return 1

    def save(e):
        cat = (f_cat.value or "").strip()
        val = (f_val.value or "").strip()
        if not cat or not val:
            error.value = "Category and Value are required."
            page.update()
            return
        if is_edit:
            existing.reference = (f_ref.value or "").strip() or None
            existing.category = cat
            existing.value = val
            existing.quantity = _qty()
            existing.is_optional = 1 if f_opt.value else 0
            store.update_bom_item(existing)
        else:
            store.add_bom_item(BOMItem(
                id=0, project_id=project.id,
                reference=(f_ref.value or "").strip() or None,
                category=cat, value=val, quantity=_qty(),
                is_optional=1 if f_opt.value else 0,
            ))
        _ui.close_dialog(page, dlg)
        app.render()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit BOM item" if is_edit else "Add BOM item"),
        content=ft.Container(
            width=460,
            content=ft.Column(
                [
                    ft.Row([f_ref, f_qty], spacing=12, wrap=True),
                    ft.Row([f_cat, f_val], spacing=12, wrap=True),
                    f_opt,
                    error,
                ],
                spacing=10, tight=True,
            ),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: _ui.close_dialog(page, dlg)),
            ft.FilledButton("Save", on_click=save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def _delete_bom_dialog(app, item):
    page = app.page
    store = app.store

    def do_delete(e):
        store.delete_bom_item(item.id)
        _ui.close_dialog(page, dlg)
        app.render()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Delete BOM item?"),
        content=ft.Text("Remove {} {} from this BOM?".format(item.category, item.value)),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: _ui.close_dialog(page, dlg)),
            ft.FilledButton("Delete", on_click=do_delete,
                            style=ft.ButtonStyle(bgcolor=ft.Colors.RED)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


# =====================================================================
# Panels
# =====================================================================
def _project_list(app, projects, selected_id):
    tiles = []
    for p in projects:
        tier_key, _status = _status_for_project(app, p)
        if tier_key:
            _label, color = _TIER_META[tier_key]
        else:
            color = ft.Colors.ON_SURFACE_VARIANT
        subtitle = p.effect_type or p.status
        tiles.append(
            ft.ListTile(
                leading=ft.Container(width=10, height=10, border_radius=5, bgcolor=color),
                title=ft.Text(p.name, weight=ft.FontWeight.W_600),
                subtitle=ft.Text(subtitle, color=ft.Colors.ON_SURFACE_VARIANT),
                selected=(p.id == selected_id),
                on_click=(lambda e, pid=p.id: _select(app, pid)),
            )
        )
    if not tiles:
        tiles = [ft.Text("No projects yet.", italic=True,
                         color=ft.Colors.ON_SURFACE_VARIANT)]
    return ft.Container(
        width=300,
        content=ft.Column(
            [
                ft.Row([ft.Text("Projects", size=20, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.IconButton(ft.Icons.ADD, tooltip="New project",
                                      on_click=lambda e: _ui.open_dialog(
                                          app.page, _project_dialog(app)))],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=8),
                ft.Column(tiles, spacing=0, scroll=ft.ScrollMode.AUTO, expand=True),
            ],
            spacing=8, expand=True,
        ),
    )


def _readiness_banner(tier_key, status):
    if tier_key is None:
        return ft.Container(
            padding=12, border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.ON_SURFACE_VARIANT),
            content=ft.Text("No BOM rows yet -- add parts to compute readiness.",
                            color=ft.Colors.ON_SURFACE_VARIANT),
        )
    label, color = _TIER_META[tier_key]
    if status.missing_count == 0:
        detail = "All required parts in stock."
    else:
        detail = "{} part(s) short.".format(status.missing_count)
    return ft.Container(
        padding=12, border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.12, color),
        content=ft.Row(
            [
                ft.Container(width=12, height=12, border_radius=6, bgcolor=color),
                ft.Text(label, weight=ft.FontWeight.BOLD, size=16, color=color),
                ft.Container(expand=True),
                ft.Text(detail, color=ft.Colors.ON_SURFACE_VARIANT),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _missing_section(status):
    if status is None or not status.missing_parts:
        return None
    chips = []
    for mp in status.missing_parts:
        ref = (mp.reference + " ") if mp.reference else ""
        chips.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.RED),
                content=ft.Text("{}{} {} ×{}".format(ref, mp.category, mp.value, mp.shortfall),
                                size=12, color=ft.Colors.RED),
            )
        )
    return ft.Column(
        [
            ft.Text("Missing parts", size=15, weight=ft.FontWeight.W_600),
            ft.Row(chips, wrap=True, spacing=8, run_spacing=8),
        ],
        spacing=8,
    )


def _bom_section(app, project):
    store = app.store
    items = store.list_bom_items(project_id=project.id)
    items.sort(key=lambda b: (b.category.lower(), b.value.lower()))

    rows = []
    for b in items:
        ref = b.reference or "-"
        tags = []
        if b.is_optional:
            tags.append("optional")
        tag_str = ("  ·  " + ", ".join(tags)) if tags else ""
        rows.append(
            ft.Row(
                [
                    ft.Container(width=70, content=ft.Text(ref, size=13,
                                 color=ft.Colors.ON_SURFACE_VARIANT)),
                    ft.Container(expand=True, content=ft.Text(
                        "{} {}{}".format(b.category, b.value, tag_str), size=14)),
                    ft.Container(width=48, content=ft.Text("×{}".format(b.quantity),
                                 size=13, text_align=ft.TextAlign.RIGHT)),
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Edit", icon_size=18,
                                  on_click=lambda e, it=b: _ui.open_dialog(
                                      app.page, _bom_dialog(app, project, it))),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Delete", icon_size=18,
                                  icon_color=ft.Colors.RED,
                                  on_click=lambda e, it=b: _ui.open_dialog(
                                      app.page, _delete_bom_dialog(app, it))),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=4,
            )
        )
    if not rows:
        rows = [ft.Text("No BOM items. Add the first part.", italic=True,
                        color=ft.Colors.ON_SURFACE_VARIANT)]

    return ft.Column(
        [
            ft.Row([ft.Text("Bill of materials", size=15, weight=ft.FontWeight.W_600),
                    ft.Container(expand=True),
                    ft.FilledButton("Add BOM item", icon=ft.Icons.ADD,
                                    on_click=lambda e: _ui.open_dialog(
                                        app.page, _bom_dialog(app, project)))],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Column(rows, spacing=2),
        ],
        spacing=10,
    )


def _detail_panel(app, project):
    if project is None:
        return ft.Container(
            expand=True, alignment=ft.alignment.center,
            content=ft.Column(
                [ft.Icon(ft.Icons.DEVELOPER_BOARD_OUTLINED, size=48,
                         color=ft.Colors.ON_SURFACE_VARIANT),
                 ft.Text("Select a project to see its BOM and readiness.",
                         color=ft.Colors.ON_SURFACE_VARIANT)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
            ),
        )

    tier_key, status = _status_for_project(app, project)

    header = ft.Row(
        [
            ft.Column(
                [
                    ft.Text(project.name, size=24, weight=ft.FontWeight.BOLD),
                    ft.Text("{}  •  {}".format(project.effect_type or "no type",
                                               project.status),
                            color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                spacing=2, tight=True, expand=True,
            ),
            ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Delete project",
                          icon_color=ft.Colors.RED,
                          on_click=lambda e: _ui.open_dialog(
                              app.page, _delete_project_dialog(app, project))),
        ],
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    controls = [header]
    if project.description:
        controls.append(ft.Text(project.description, color=ft.Colors.ON_SURFACE_VARIANT))
    controls.append(_readiness_banner(tier_key, status))
    missing = _missing_section(status)
    if missing is not None:
        controls.append(missing)
    controls.append(ft.Divider(height=12))
    controls.append(_bom_section(app, project))

    return ft.Container(
        expand=True,
        content=ft.Column(controls, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True),
    )


def build(app):
    store = app.store
    projects = store.list_projects()
    projects.sort(key=lambda p: p.name.lower())

    selected_id = _selected_id(app)
    selected = None
    if selected_id is not None:
        selected = store.get_project(selected_id)
        if selected is None:  # stale id (e.g. deleted)
            app._proj_selected = None  # type: ignore[attr-defined]

    return ft.Row(
        [
            _project_list(app, projects, selected_id),
            ft.VerticalDivider(width=1),
            _detail_panel(app, selected),
        ],
        expand=True, vertical_alignment=ft.CrossAxisAlignment.START,
    )
