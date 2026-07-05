# SPDX-License-Identifier: MIT
"""Flet view builders for Pedal Workshop.

Each module exposes ``build(app)`` returning a Flet control tree for its screen.
"""

# Importing _ui installs the layout-helper compatibility shims (ft.border.all,
# ft.padding.*, ft.alignment.*) that dashboard.py and the other views rely on.
# Done here so the shims are in place as soon as the views package is imported,
# before any view's build() runs -- including dashboard.py, which does not
# import _ui itself.
from . import _ui as _ui  # noqa: F401
