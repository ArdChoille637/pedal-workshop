# SPDX-License-Identifier: MIT
"""Tests for pipeline/tools/score_pilot.py — truth-sheet scoring against extractions."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from score_pilot import (  # noqa: E402
    report, score_dir, score_one, semi_compare, summarize, taper_of, value_compare,
)


def truth(*rows):
    return [{"ref": r, "cls": c, "type": t, "value": v} for r, c, t, v in rows]


def doc(parts, nets=None, confidence="high"):
    return {"parts": [{"ref": r, "type": t, "value": v, "pins": 2} for r, t, v in parts],
            "nets": nets or [], "confidence": confidence, "issues": []}


T = truth(("R1", "R", "resistor", "10k"), ("C1", "C", "capacitor", "100n"),
          ("Q1", "S", "transistor", "2N3904"), ("RV1", "P", "potentiometer", "100kA"))
D = doc([("R1", "resistor", "10k"), ("C1", "capacitor", ".1uf"),
         ("Q1", "transistor", "2N3904"), ("RV1", "potentiometer", "100k LOG")])


def test_perfect_with_equivalent_forms():
    r = score_one("x", T, D, [])
    assert r["hit"] == 4 == r["truth_n"] == r["ext_n"]
    assert r["vstat"]["passive"] == [3, 3, 3]          # .1uf == 100n; 100kA == 100k LOG
    assert r["vstat"]["semi"] == [1, 1]
    assert r["vstat"]["taper"] == [1, 1]               # A == LOG


def test_value_wrong_missing_extra():
    d = doc([("R1", "resistor", "100k"), ("R9", "resistor", "1k"), ("Q1", "transistor", "2N3904")])
    r = score_one("x", T, d, [])
    v = {(x["ref"], x["verdict"]) for x in r["diff"]}
    assert ("R1", "value-wrong") in v and ("C1", "missing-in-extraction") in v
    assert ("R9", "extra-in-extraction") in v and ("Q1", "match") in v
    assert r["vstat"]["passive"][0] == 0


@pytest.mark.parametrize("cls,a,b,expected", [
    ("R", "4k7", "4.7k", "match"), ("R", "10000", "10k", "match"), ("R", "1M", "1meg", "match"),
    ("R", "10k", "100k", "wrong"),
    ("C", ".1uf", "100n", "match"), ("C", "47p", "47pF", "match"), ("C", "10u/16V", "10uF", "match"),
    ("C", ".022", "0.022", "match"), ("C", ".022", "22n", "unit-ambiguous"),
    ("C", ".022", "22p", "wrong"),
    ("P", "100kA", "100k", "match"), ("P", "B10k", "10k LIN", "match"),
])
def test_value_compare(cls, a, b, expected):
    assert value_compare(cls, a, b) == expected


@pytest.mark.parametrize("a,b,expected", [
    ("LM324", "324", "match"), ("2N3904", "2n3904", "match"), ("TL072", "TL082", "wrong"),
    ("1N4148", "1N914", "wrong"), ("", "LM358", "wrong"),
])
def test_semi_compare(a, b, expected):
    assert semi_compare(a, b) == expected


def test_taper_extraction():
    assert taper_of("100kA") == "A" and taper_of("B10k") == "B" and taper_of("10k LIN") == "B"
    assert taper_of("50k rev") == "C" and taper_of("100k") is None


def test_taper_disagreement():
    t = truth(("RV1", "P", "potentiometer", "100kA"))
    r = score_one("x", t, doc([("RV1", "potentiometer", "100kB")]), [])
    assert r["vstat"]["passive"][:1] == [1] and r["vstat"]["taper"] == [0, 1]


def test_jacks_and_switches_ignored_both_sides():
    d = doc([("R1", "resistor", "10k"), ("J1", "jack", "unknown"), ("SW1", "switch", "3PDT")])
    r = score_one("x", truth(("R1", "R", "resistor", "10k")), d, [])
    assert r["ext_n"] == 1 and r["hit"] == 1


def test_invented_refs_still_score_on_bom_bag():
    d = doc([("R10", "resistor", "10k"), ("C20", "capacitor", "100n"),
             ("Q30", "transistor", "2N3904"), ("P1", "potentiometer", "100k")])
    r = score_one("x", T, d, [])
    assert r["hit"] == 4            # every (class, value) is found...
    assert r["ref_matched"] == 0    # ...even though no reference designator lines up


def test_netlist_f1_only_for_lint_candidates():
    nets = [{"name": "A", "pins": ["R1.1", "C1.1"]}, {"name": "B", "pins": ["R1.2", "C1.2"]}]
    d = doc([("R1", "resistor", "10k"), ("C1", "capacitor", "100n")], nets)
    tn = [{"R1.1", "C1.1"}, {"R1.2", "C1.2"}]
    r = score_one("x", truth(("R1", "R", "resistor", "10k"), ("C1", "C", "capacitor", "100n")), d, tn)
    assert r["tier"] == "netlist-candidate" and r["net"] == {"tp": 2, "fp": 0, "fn": 0}
    bad = score_one("x", truth(("R1", "R", "resistor", "10k"), ("C1", "C", "capacitor", "100n")),
                    doc([("R1", "resistor", "10k"), ("C1", "capacitor", "100n")],
                        [{"name": "A", "pins": ["R1.1", "C1.2"]}]), tn)
    assert bad["net"] is None                             # fails lint coverage -> not scored


def _write(tmp: Path, slug: str, truth_rows: str, d: dict):
    (tmp / f"{slug}.truth.csv").write_text("ref,type,value\n" + truth_rows)
    (tmp / "ex").mkdir(exist_ok=True)
    (tmp / "ex" / f"{slug}.json").write_text(json.dumps(d))


def test_blank_sheets_skipped_and_report_runs(tmp_path):
    _write(tmp_path, "blank", "", D)
    _write(tmp_path, "a", "R1,resistor,10k\nC1,capacitor,100n\n", doc([("R1", "resistor", "10k"), ("C1", "capacitor", "100n")]))
    rows = score_dir(tmp_path, tmp_path / "ex")
    assert [r["slug"] for r in rows] == ["a"]
    text = report(rows, tmp_path, tmp_path / "ex")
    assert "scored 1 of 2" in text and "BOM recall" in text and "INCONCLUSIVE" in text


def test_nothing_to_score_message(tmp_path):
    (tmp_path / "x.truth.csv").write_text("ref,type,value\n")
    assert "nothing to score yet" in report([], tmp_path, tmp_path)


def test_stop_verdict_when_extraction_is_poor(tmp_path):
    for i in range(3):
        _write(tmp_path, f"s{i}", "R1,resistor,10k\nR2,resistor,22k\nC1,capacitor,100n\nC2,capacitor,47n\n",
               doc([("R1", "resistor", "999k"), ("C1", "capacitor", "1u")]))
    text = report(score_dir(tmp_path, tmp_path / "ex"), tmp_path, tmp_path / "ex")
    assert "STOP" in text


def test_bootstrap_is_deterministic_and_needs_two_schematics():
    rows = [score_one(f"s{i}", T, D, []) for i in range(4)]
    assert summarize(rows)["recall"] == summarize(rows)["recall"]
    assert summarize(rows[:1])["recall"][1] is None
