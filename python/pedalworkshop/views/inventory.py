# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Inventory view: searchable component list with inline +/- and CRUD dialogs.

Filter state (search text, category, low-stock-only) is kept on the ``app``
object so it survives the whole-view rebuilds that ``app.render()`` triggers.
"""

import flet as ft

from ..models import Component
from . import _ui


# Filter state lives on the app so app.render() rebuilds don't reset it.
def _state(app):
    st = getattr(app, "_inv_state", None)
    if st is None:
        st = {"query": "", "category": "All", "low_only": False}
        app._inv_state = st  # type: ignore[attr-defined]
    return st


# Component has no single "name"; build a searchable haystack from its fields.
def _name_hay(comp):
    bits = [comp.category, comp.value, comp.subcategory or "", comp.package or "",
            comp.mpn or "", comp.manufacturer or "", comp.description or "",
            comp.location or "", comp.notes or ""]
    return " ".join(b for b in bits if b)


def _matches(comp, query, category, low_only):
    if low_only and not comp.is_low_stock:
        return False
    if category != "All" and comp.category != category:
        return False
    if query:
        if query.lower() not in _name_hay(comp).lower():
            return False
    return True


def _component_dialog(app, existing=None):
    """Build an add/edit dialog for a component."""
    store = app.store
    page = app.page
    is_edit = existing is not None

    f_category = ft.TextField(label="Category *", value=(existing.category if is_edit else ""),
                              dense=True, width=240,
                              hint_text="e.g. resistor, capacitor, ic")
    f_value = ft.TextField(label="Value *", value=(existing.value if is_edit else ""),
                           dense=True, width=240, hint_text="e.g. 10k, 100n, TL072")
    f_qty = ft.TextField(label="Quantity", value=str(existing.quantity if is_edit else 0),
                         dense=True, width=140, keyboard_type=ft.KeyboardType.NUMBER)
    f_min = ft.TextField(label="Min quantity", value=str(existing.min_quantity if is_edit else 0),
                         dense=True, width=140, keyboard_type=ft.KeyboardType.NUMBER)
    f_package = ft.TextField(label="Package", value=(existing.package or "" if is_edit else ""),
                             dense=True, width=200)
    f_mpn = ft.TextField(label="MPN", value=(existing.mpn or "" if is_edit else ""),
                         dense=True, width=200)
    f_location = ft.TextField(label="Location", value=(existing.location or "" if is_edit else ""),
                              dense=True, width=200)
    f_notes = ft.TextField(label="Notes", value=(existing.notes or "" if is_edit else ""),
                           dense=True, width=420, multiline=True, min_lines=1, max_lines=3)
    error = ft.Text("", color=ft.Colors.RED, size=12)

    def _to_int(field, default=0):
        try:
            return max(0, int(str(field.value).strip() or default))
        except ValueError:
            return default

    def save(e):
        cat = (f_category.value or "").strip()
        val = (f_value.value or "").strip()
        if not cat or not val:
            error.value = "Category and Value are required."
            page.update()
            return
        if is_edit:
            existing.category = cat
            existing.value = val
            existing.quantity = _to_int(f_qty)
            existing.min_quantity = _to_int(f_min)
            existing.package = (f_package.value or "").strip() or None
            existing.mpn = (f_mpn.value or "").strip() or None
            existing.location = (f_location.value or "").strip() or None
            existing.notes = (f_notes.value or "").strip() or None
            store.update_component(existing)
        else:
            store.add_component(Component(
                id=0, category=cat, value=val,
                quantity=_to_int(f_qty), min_quantity=_to_int(f_min),
                package=(f_package.value or "").strip() or None,
                mpn=(f_mpn.value or "").strip() or None,
                location=(f_location.value or "").strip() or None,
                notes=(f_notes.value or "").strip() or None,
            ))
        _ui.close_dialog(page, dlg)
        app.render()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit component" if is_edit else "Add component"),
        content=ft.Container(
            width=520,
            content=ft.Column(
                [
                    ft.Row([f_category, f_value], spacing=12, wrap=True),
                    ft.Row([f_qty, f_min, f_package], spacing=12, wrap=True),
                    ft.Row([f_mpn, f_location], spacing=12, wrap=True),
                    f_notes,
                    error,
                ],
                spacing=10, tight=True, scroll=ft.ScrollMode.AUTO,
            ),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: _ui.close_dialog(page, dlg)),
            ft.FilledButton("Save", on_click=save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def _delete_dialog(app, comp):
    page = app.page
    store = app.store

    def do_delete(e):
        store.delete_component(comp.id)
        _ui.close_dialog(page, dlg)
        app.render()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Delete component?"),
        content=ft.Text("Remove {} {} from inventory? This cannot be undone."
                        .format(comp.category, comp.value)),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: _ui.close_dialog(page, dlg)),
            ft.FilledButton("Delete", on_click=do_delete,
                            style=ft.ButtonStyle(bgcolor=ft.Colors.RED)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def _row(app, comp):
    store = app.store
    low = comp.is_low_stock
    tint = ft.Colors.with_opacity(0.10, ft.Colors.RED) if low else None

    def adjust(delta):
        def handler(e):
            store.adjust_quantity(comp.id, delta)
            app.render()
        return handler

    subtitle_bits = [comp.category]
    if comp.package:
        subtitle_bits.append(comp.package)
    if comp.location:
        subtitle_bits.append("loc " + comp.location)
    subtitle = "  •  ".join(subtitle_bits)

    qty_label = ft.Text(str(comp.quantity), weight=ft.FontWeight.BOLD, size=15,
                        color=(ft.Colors.RED if low else None))
    min_label = ("/ min {}".format(comp.min_quantity)
                 if comp.min_quantity > 0 else "")

    return ft.Container(
        bgcolor=tint,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        content=ft.Row(
            [
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        [
                            ft.Row([
                                ft.Text(comp.value, weight=ft.FontWeight.W_600, size=15),
                                *([ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.RED, size=16)]
                                  if low else []),
                            ], spacing=6, tight=True),
                            ft.Text(subtitle, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        spacing=1, tight=True,
                    ),
                ),
                ft.Row(
                    [
                        ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, tooltip="-1",
                                      on_click=adjust(-1)),
                        ft.Column([qty_label,
                                   ft.Text(min_label, size=10,
                                           color=ft.Colors.ON_SURFACE_VARIANT)],
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                  spacing=0, tight=True, width=54),
                        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, tooltip="+1",
                                      on_click=adjust(1)),
                        ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Edit",
                                      on_click=lambda e, c=comp: _ui.open_dialog(
                                          app.page, _component_dialog(app, c))),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Delete",
                                      icon_color=ft.Colors.RED,
                                      on_click=lambda e, c=comp: _ui.open_dialog(
                                          app.page, _delete_dialog(app, c))),
                    ],
                    spacing=0, tight=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def build(app):
    store = app.store
    page = app.page
    st = _state(app)

    components = store.list_components()
    categories = ["All"] + store.component_categories()
    if st["category"] not in categories:
        st["category"] = "All"

    # --- filter controls -------------------------------------------------
    def on_query(e):
        st["query"] = e.control.value or ""
        app.render()

    def on_category(e):
        st["category"] = e.control.value or "All"
        app.render()

    def on_low(e):
        st["low_only"] = bool(e.control.value)
        app.render()

    def add_new(e):
        _ui.open_dialog(page, _component_dialog(app, None))

    search = ft.TextField(
        label="Search", value=st["query"], dense=True, expand=True,
        prefix_icon=ft.Icons.SEARCH, on_change=on_query,
        hint_text="name, value, category, MPN…",
    )
    cat_dd = ft.Dropdown(
        label="Category", value=st["category"], dense=True, width=200,
        options=[ft.DropdownOption(key=c, text=c) for c in categories],
        on_select=on_category,
    )
    low_switch = ft.Switch(label="Low stock only", value=st["low_only"], on_change=on_low)

    controls_row = ft.Row(
        [search, cat_dd, low_switch,
         ft.FilledButton("Add component", icon=ft.Icons.ADD, on_click=add_new)],
        spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # --- filtered rows ---------------------------------------------------
    visible = [c for c in components
               if _matches(c, st["query"], st["category"], st["low_only"])]
    visible.sort(key=lambda c: (c.category.lower(), c.value.lower()))

    if not visible:
        body = ft.Container(
            padding=40,
            content=ft.Column(
                [ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=48,
                         color=ft.Colors.ON_SURFACE_VARIANT),
                 ft.Text("No components match your filters.",
                         color=ft.Colors.ON_SURFACE_VARIANT)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
            ),
            alignment=ft.alignment.center,
        )
    else:
        body = ft.Column([_row(app, c) for c in visible],
                         spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)

    count_note = ft.Text(
        "{} of {} components".format(len(visible), len(components)),
        size=12, color=ft.Colors.ON_SURFACE_VARIANT,
    )

    return ft.Column(
        [
            ft.Row([ft.Text("Inventory", size=26, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True), count_note],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            controls_row,
            ft.Divider(height=10),
            body,
        ],
        spacing=12, expand=True,
    )
