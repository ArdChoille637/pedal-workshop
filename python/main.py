# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pedal Workshop Contributors
"""Pedal Workshop -- Flet desktop app entry point.

Run with:  python main.py
"""

import flet as ft

from pedalworkshop.app import main

if __name__ == "__main__":
    # Per the shared spec. On Flet 0.80+ ft.app() is a thin (deprecated) wrapper
    # around ft.run() that still accepts target=; it forwards the callable
    # positionally, so this launches cleanly on the pinned 0.85.
    ft.app(target=main)
