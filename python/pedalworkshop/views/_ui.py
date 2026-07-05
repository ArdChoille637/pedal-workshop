# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Small UI helpers shared across the Flet views.

Centralises the two bits of Flet API that changed between releases so the view
modules don't each have to know the details:

* Dialogs -- this project targets Flet 0.85, which uses ``page.show_dialog`` /
  ``page.pop_dialog`` (the old ``page.open`` / ``page.close`` were removed).
  ``open_dialog`` / ``close_dialog`` wrap those, falling back to the older API
  if the app is ever run against an earlier Flet.
* Directory picking -- ``FilePicker.get_directory_path`` is an async coroutine
  in 0.85 and returns the chosen path directly (no result-event callback).
  ``pick_directory`` drives it via ``page.run_task`` and invokes a plain
  callback with the path (or None if cancelled), so callers stay synchronous.
"""

import flet as ft


# --------------------------------------------------------------- compat shims
def _install_layout_compat():
    """Restore the ``ft.border.all`` / ``ft.padding.*`` / ``ft.alignment.*``
    helper *functions* that older Flet exposed as module-level callables.

    Flet 0.70+ moved these onto the ``Border`` / ``Padding`` / ``Alignment``
    classes as classmethods and dropped the module-level helpers, but the
    reference views (e.g. dashboard.py) and these ports were written against the
    older, more readable ``ft.border.all(...)`` style. We re-attach thin
    forwarders so that style keeps working on the installed Flet without
    rewriting every call site. No-ops on a Flet that still has them.
    """
    # ft.border.all(width, color, side=None)
    if not hasattr(ft.border, "all") and hasattr(ft.Border, "all"):
        ft.border.all = ft.Border.all  # type: ignore[attr-defined]

    # ft.padding.all/symmetric/only(...)
    for name in ("all", "symmetric", "only"):
        if not hasattr(ft.padding, name) and hasattr(ft.Padding, name):
            setattr(ft.padding, name, getattr(ft.Padding, name))

    # ft.alignment.<preset> constants (Alignment(x, y)); add the ones we use.
    _presets = {
        "center": (0.0, 0.0),
        "center_left": (-1.0, 0.0),
        "center_right": (1.0, 0.0),
        "top_center": (0.0, -1.0),
        "top_left": (-1.0, -1.0),
        "bottom_center": (0.0, 1.0),
    }
    for pname, (x, y) in _presets.items():
        if not hasattr(ft.alignment, pname):
            try:
                setattr(ft.alignment, pname, ft.Alignment(x, y))
            except Exception:
                pass


_install_layout_compat()


# --------------------------------------------------------------------- dialogs
def open_dialog(page: ft.Page, dialog: ft.AlertDialog) -> None:
    """Show a modal dialog (version-tolerant)."""
    show = getattr(page, "show_dialog", None)
    if callable(show):
        show(dialog)
        return
    # Older Flet fallback (<= 0.2x): overlay + open flag, or page.open.
    opener = getattr(page, "open", None)
    if callable(opener):
        opener(dialog)
        return
    if dialog not in page.overlay:
        page.overlay.append(dialog)
    dialog.open = True
    page.update()


def close_dialog(page: ft.Page, dialog: ft.AlertDialog) -> None:
    """Dismiss the top-most / given modal dialog (version-tolerant)."""
    popper = getattr(page, "pop_dialog", None)
    if callable(popper):
        popper()
        return
    closer = getattr(page, "close", None)
    if callable(closer):
        closer(dialog)
        return
    dialog.open = False
    page.update()


# ------------------------------------------------------------- directory picker
def pick_directory(page: ft.Page, on_pick, dialog_title: str = "Choose folder"):
    """Prompt for a directory, then call ``on_pick(path)`` with the result.

    ``path`` is None if the user cancels. A ``FilePicker`` is registered in
    ``page.services`` on first use and reused thereafter.
    """
    picker = getattr(page, "_pw_dir_picker", None)
    if picker is None:
        picker = ft.FilePicker()
        try:
            page.services.append(picker)
        except Exception:
            # Very old Flet kept pickers in the overlay.
            page.overlay.append(picker)
        page._pw_dir_picker = picker  # type: ignore[attr-defined]
        page.update()

    async def _run():
        path = await picker.get_directory_path(dialog_title=dialog_title)
        on_pick(path)

    page.run_task(_run)


# ---------------------------------------------------------------- misc widgets
def form_field(label: str, value: str = "", multiline: bool = False,
               width=None, keyboard=None, hint: str = "") -> ft.TextField:
    """A consistently-styled TextField for the add/edit dialogs."""
    return ft.TextField(
        label=label,
        value=value or "",
        hint_text=hint or None,
        multiline=multiline,
        min_lines=1,
        max_lines=4 if multiline else 1,
        dense=True,
        width=width,
        keyboard_type=keyboard,
    )


def snack(page: ft.Page, message: str) -> None:
    """Show a transient message (best-effort; ignored if unsupported).

    In Flet 0.85 a SnackBar is a DialogControl, so it is shown through the same
    ``show_dialog`` overlay path as modal dialogs.
    """
    try:
        bar = ft.SnackBar(content=ft.Text(message))
        show = getattr(page, "show_dialog", None)
        if callable(show):
            show(bar)
            return
        opener = getattr(page, "open", None)
        if callable(opener):
            opener(bar)
            return
        page.overlay.append(bar)
        bar.open = True
        page.update()
    except Exception:
        pass
