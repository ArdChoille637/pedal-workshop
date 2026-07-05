# SPDX-License-Identifier: MIT
"""Tests for the Build Analyzer (normalize_value + tier classification)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pedalworkshop.build_analyzer import normalize_value, analyze, summary
from pedalworkshop.models import Component, Project, BOMItem


# ---------------------------------------------------------------- normalize
def test_normalize_european_shorthand():
    assert normalize_value("4k7") == "4.7k"
    assert normalize_value("2n2") == "2.2n"
    assert normalize_value("1m5") == "1.5m"


def test_normalize_bare_r_suffix():
    assert normalize_value("470r") == "470"
    assert normalize_value("470R") == "470"


def test_normalize_ohm_word_and_case():
    assert normalize_value("10K Ohm") == "10k"
    assert normalize_value("10k ohm") == "10k"
    assert normalize_value("470 ohms") == "470"


def test_normalize_unicode_ohm_sign():
    assert normalize_value("470Ω") == "470"      # Ω OHM SIGN
    assert normalize_value("10kΩ") == "10k"      # Ω greek capital omega


def test_normalize_stray_r_after_multiplier():
    assert normalize_value("4.7kr") == "4.7k"


def test_normalize_trims_and_lowercases():
    assert normalize_value("  TL072  ") == "tl072"


# ------------------------------------------------------------ helper builders
def _comp(cid, category, value, qty):
    return Component(id=cid, category=category, value=value, quantity=qty, min_quantity=0)


def _bom(bid, pid, category, value, qty=1, is_optional=0, reference=None):
    return BOMItem(id=bid, project_id=pid, category=category, value=value,
                   quantity=qty, is_optional=is_optional, reference=reference)


# -------------------------------------------------- demand aggregation
def test_demand_aggregation_across_duplicate_rows():
    """Two BOM rows of 10k resistor (qty 1 each) vs 1 on hand -> shortfall 1."""
    project = Project(id=1, name="P", slug="p")
    boms = [
        _bom(1, 1, "resistor", "10k", 1, reference="R1"),
        _bom(2, 1, "resistor", "10k", 1, reference="R2"),
    ]
    comps = [_comp(1, "resistor", "10k", 1)]
    tiers = analyze([project], boms, comps)
    # Aggregated demand=2, onhand=1 -> exactly one missing part.
    assert len(tiers.arna13) == 1
    st = tiers.arna13[0]
    assert st.missing_count == 1
    assert st.missing_parts[0].shortfall == 1


def test_normalization_matches_stock():
    """BOM '4k7' should match on-hand '4.7k'."""
    project = Project(id=1, name="P", slug="p")
    boms = [_bom(1, 1, "resistor", "4k7", 1)]
    comps = [_comp(1, "Resistor", "4.7k", 5)]
    tiers = analyze([project], boms, comps)
    assert len(tiers.ready) == 1


# -------------------------------------------------- enclosure + optional
def test_enclosure_and_optional_excluded():
    """Enclosure and optional rows never count toward missing total."""
    project = Project(id=1, name="P", slug="p")
    boms = [
        _bom(1, 1, "resistor", "10k", 1),                 # in stock
        _bom(2, 1, "enclosure", "1590BB", 1),             # excluded (enclosure)
        _bom(3, 1, "hardware", "knob", 1, is_optional=1), # excluded (optional)
    ]
    comps = [_comp(1, "resistor", "10k", 5)]  # no enclosure/knob in stock
    tiers = analyze([project], boms, comps)
    # Only the resistor counts, and it's in stock -> Ready.
    assert len(tiers.ready) == 1
    assert tiers.ready[0].missing_count == 0


def test_enclosure_case_insensitive_exclusion():
    project = Project(id=1, name="P", slug="p")
    boms = [
        _bom(1, 1, " Enclosure ", "1590B", 1),  # trimmed+lowered -> excluded
    ]
    comps = []
    tiers = analyze([project], boms, comps)
    # Only row is the enclosure, which is excluded -> 0 missing -> Ready.
    assert len(tiers.ready) == 1


# -------------------------------------------------- tier boundaries 0/3/4
def test_tier_boundary_zero_is_ready():
    project = Project(id=1, name="P", slug="p")
    boms = [_bom(1, 1, "resistor", "10k", 1)]
    comps = [_comp(1, "resistor", "10k", 5)]
    tiers = analyze([project], boms, comps)
    assert len(tiers.ready) == 1
    assert len(tiers.arna13) == 0
    assert len(tiers.arna4plus) == 0


def test_tier_boundary_three_is_arna13():
    """Exactly 3 distinct missing parts -> ARNA 1-3 (upper bound)."""
    project = Project(id=1, name="P", slug="p")
    boms = [
        _bom(1, 1, "resistor", "10k", 1),
        _bom(2, 1, "resistor", "22k", 1),
        _bom(3, 1, "resistor", "47k", 1),
    ]
    comps = []  # all missing
    tiers = analyze([project], boms, comps)
    assert len(tiers.arna13) == 1
    assert tiers.arna13[0].missing_count == 3
    assert len(tiers.arna4plus) == 0


def test_tier_boundary_four_is_arna4plus():
    """Exactly 4 distinct missing parts -> ARNA 4+."""
    project = Project(id=1, name="P", slug="p")
    boms = [
        _bom(1, 1, "resistor", "10k", 1),
        _bom(2, 1, "resistor", "22k", 1),
        _bom(3, 1, "resistor", "47k", 1),
        _bom(4, 1, "resistor", "100k", 1),
    ]
    comps = []
    tiers = analyze([project], boms, comps)
    assert len(tiers.arna4plus) == 1
    assert tiers.arna4plus[0].missing_count == 4
    assert len(tiers.arna13) == 0


# -------------------------------------------------- misc
def test_project_with_no_bom_is_skipped():
    project = Project(id=1, name="Empty", slug="empty")
    tiers = analyze([project], [], [])
    assert len(tiers.ready) == 0
    assert len(tiers.arna13) == 0
    assert len(tiers.arna4plus) == 0


def test_summary_counts():
    project = Project(id=1, name="P", slug="p", status="prototype")
    boms = [_bom(1, 1, "resistor", "10k", 1)]
    comps = [
        _comp(1, "resistor", "10k", 5),
        Component(id=2, category="resistor", value="22k", quantity=1, min_quantity=5),  # low stock
    ]
    tiers = analyze([project], boms, comps)
    s = summary(comps, [project], tiers)
    assert s.total_components == 6      # 5 + 1
    assert s.total_unique_parts == 2
    assert s.total_projects == 1
    assert s.active_builds == 1         # prototype
    assert s.low_stock_count == 1
    assert s.ready_count == 1
