# SPDX-License-Identifier: MIT
"""Tests for pipeline/lint_extractions.py — value parsing and structural lint."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lint_extractions import is_e24, lint, parse_value, split_pin  # noqa: E402


@pytest.mark.parametrize("raw,kind,num", [
    ("10k", "resistor", 1e4), ("4k7", "resistor", 4700.0), ("470r", "resistor", 470.0),
    ("470R", "resistor", 470.0), ("1M", "resistor", 1e6), ("1meg", "resistor", 1e6),
    ("2.2k ohm", "resistor", 2200.0), ("100kΩ", "resistor", 1e5),
    ("100n", "capacitor", 1e-7), ("0.1u", "capacitor", 1e-7), (".1uf", "capacitor", 1e-7),
    ("100nF", "capacitor", 1e-7), ("47p", "capacitor", 4.7e-11), ("2u2", "capacitor", 2.2e-6),
    ("1uF 50v", "capacitor", 1e-6), ("4n7", "capacitor", 4.7e-9),
    ("10K", "resistor", 1e4), ("4.7K", "resistor", 4700.0), ("2K2", "resistor", 2200.0),
    ("1000P", "capacitor", 1e-9), ("10u/16V", "capacitor", 1e-5), ("0.1uF/50", "capacitor", 1e-7),
])
def test_equivalent_forms_parse(raw, kind, num):
    got, status = parse_value(raw, kind)
    assert status == "ok"
    assert got == pytest.approx(num, rel=1e-9)


def test_equivalent_values_agree():
    # The pairs the Swift normalizeValue does NOT unify today (reply finding 3).
    assert parse_value("100n", "capacitor")[0] == pytest.approx(parse_value("0.1u", "capacitor")[0])
    assert parse_value("100nF", "capacitor")[0] == pytest.approx(parse_value(".1uf", "capacitor")[0])
    assert parse_value("10000", "resistor")[0] == pytest.approx(parse_value("10k", "resistor")[0])
    assert parse_value("1meg", "resistor")[0] == pytest.approx(parse_value("1M", "resistor")[0])


def test_resistor_bare_number_is_assumed_ohms():
    assert parse_value("620", "resistor") == (620.0, "assumed-unit")


@pytest.mark.parametrize("raw,kind,status", [
    (".022", "capacitor", "ambiguous"),          # uF or pF? never guess
    (".047 or .1uf", "capacitor", "ambiguous"),
    ("10k/20k", "resistor", "ambiguous"),
    ("1m", "resistor", "ambiguous"),             # lower-case m: milli-ohm is a misread
    ("1k", "capacitor", "ambiguous"),
    ("1/50", "capacitor", "ambiguous"), ("10/16", "capacitor", "ambiguous"),  # uF/V? never guess
    ("unknown", "resistor", "unknown"), ("Not Specified", "capacitor", "unknown"),
    ("", "resistor", "unknown"), (None, "capacitor", "unknown"),
    ("*k", "resistor", "ambiguous"),             # "select at test" marker, not a value
])
def test_never_guessed(raw, kind, status):
    num, st = parse_value(raw, kind)
    assert st == status and num is None


def test_e24():
    assert is_e24(4700) and is_e24(1e-7) and is_e24(220e3) and is_e24(1e6)
    assert not is_e24(4750) and not is_e24(620.5)
    assert is_e24(9.999e3)  # rounds up to 10k


def test_split_pin():
    assert split_pin("R1.2") == ("R1", "2")
    assert split_pin("IC1.A") == ("IC1", "A")
    assert split_pin("GND") == ("GND", "")


def _doc(parts, nets):
    return {"parts": parts, "nets": nets, "confidence": "high", "issues": []}


def test_full_coverage_is_netlist_candidate():
    d = _doc([{"ref": "R1", "type": "resistor", "value": "10k", "pins": 2},
              {"ref": "C1", "type": "capacitor", "value": "100n", "pins": 2}],
             [{"name": "A", "pins": ["R1.1", "C1.1"]}, {"name": "B", "pins": ["R1.2", "C1.2"]}])
    r = lint(d)
    assert r["pin_coverage"] == 1.0 and r["tier"] == "netlist-candidate"
    assert r["unconnected"] == r["dangling_refs"] == r["dup_refs"] == r["single_pin_nets"] == 0


def test_defects_are_counted():
    d = _doc([{"ref": "R1", "type": "resistor", "value": "620.5", "pins": 2},
              {"ref": "R1", "type": "resistor", "value": "unknown", "pins": 2},
              {"ref": "Q1", "type": "transistor", "value": "2N3904", "pins": 3}],
             [{"name": "A", "pins": ["R1.1", "X9.1"]}, {"name": "B", "pins": ["R1.1"]}])
    r = lint(d)
    assert r["dup_refs"] == 1
    assert r["dangling_refs"] == 1            # X9 does not exist
    assert r["single_pin_nets"] == 1
    assert r["multi_net_pins"] == 1           # R1.1 sits in two nets
    assert r["unconnected"] == 1              # Q1 is in no net
    assert r["value_issues"] == 1 and r["off_e24"] == 1
    assert r["tier"] == "parts-list-only"


def test_pin_listed_twice_in_one_net_counts_once():
    d = _doc([{"ref": "R1", "type": "resistor", "value": "10k", "pins": 2}],
             [{"name": "A", "pins": ["R1.1", "R1.1"]}])
    assert lint(d)["pins_placed"] == 1


def test_no_nets_and_no_parts():
    assert lint(_doc([{"ref": "R1", "type": "resistor", "value": "1k", "pins": 2}], []))["zero_nets"] == 1
    assert lint(_doc([], []))["tier"] == "no-parts"
