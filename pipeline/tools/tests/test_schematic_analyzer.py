"""Tests for scripts/analyze_schematics.py — extraction and normalization logic."""

import sys
from pathlib import Path

import pytest

# The script lives in scripts/, not a package — add it to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_schematics import (
    build_bom_entries,
    correct_ocr,
    extract_voltages,
    normalize_cap,
    normalize_cap_euro,
    normalize_r,
    normalize_r_euro,
)


# ---------------------------------------------------------------------------
# Resistor normalization
# ---------------------------------------------------------------------------

class TestNormalizeResistor:
    def test_kilohm(self):
        assert normalize_r("10", "k") == "10k"
        assert normalize_r("4.7", "K") == "4.7k"

    def test_megohm(self):
        assert normalize_r("1", "M") == "1M"
        assert normalize_r("2.2", "meg") == "2.2M"

    def test_bare_ohm(self):
        assert normalize_r("470", "R") == "470"
        assert normalize_r("100", "ohm") == "100"

    def test_integer_ohm_strips_decimal(self):
        assert normalize_r("470", "") == "470"

    def test_comma_decimal_separator(self):
        assert normalize_r("4,7", "k") == "4.7k"


class TestNormalizeResistorEuro:
    """4K7 European notation (IEC 60062)."""

    def test_4k7(self):
        assert normalize_r_euro("4", "K", "7") == "4.7k"

    def test_1k5(self):
        assert normalize_r_euro("1", "K", "5") == "1.5k"

    def test_2m2(self):
        assert normalize_r_euro("2", "M", "2") == "2.2M"

    def test_2r2(self):
        # 2R2 = 2.2 ohm
        assert normalize_r_euro("2", "R", "2") == "2.2"

    def test_100r(self):
        # RE_R_EURO only matches <digit><sep><digit>, not "100R" alone —
        # that's handled by the standard RE_RESISTOR with "R" unit
        assert normalize_r("100", "R") == "100"


# ---------------------------------------------------------------------------
# Capacitor normalization
# ---------------------------------------------------------------------------

class TestNormalizeCap:
    def test_nanofarad(self):
        assert normalize_cap("100", "n") == "100nF"
        assert normalize_cap("100", "nF") == "100nF"

    def test_microfarad(self):
        assert normalize_cap("47", "u") == "47uF"
        assert normalize_cap("10", "uF") == "10uF"
        assert normalize_cap("47", "µF") == "47uF"

    def test_picofarad(self):
        assert normalize_cap("220", "p") == "220pF"
        assert normalize_cap("22", "pF") == "22pF"

    def test_leading_dot(self):
        assert normalize_cap(".047", "uF") == "0.047uF"

    def test_comma_decimal(self):
        assert normalize_cap("0,1", "uF") == "0.1uF"


class TestNormalizeCapEuro:
    def test_4n7(self):
        assert normalize_cap_euro("4", "n", "7") == "4.7nF"

    def test_47u(self):
        # 47U5 = 47.5uF (rare but valid)
        assert normalize_cap_euro("47", "u", "5") == "47.5uF"

    def test_100p5(self):
        assert normalize_cap_euro("100", "p", "5") == "100.5pF"


# ---------------------------------------------------------------------------
# OCR correction
# ---------------------------------------------------------------------------

class TestCorrectOCR:
    def test_tl_zero_prefix(self):
        # The 0→O rule was removed because it fired on valid part numbers like TL072.
        # TL0072 (double-zero) cannot be safely corrected without risking real parts.
        assert correct_ocr("TL0072") == "TL0072"
        assert correct_ocr("TL072") == "TL072"

    def test_b_prefix_misread_as_8(self):
        assert correct_ocr("8C547") == "BC547"
        assert correct_ocr("8D139") == "BD139"

    def test_in_prefix_misread_as_in(self):
        # "IN4148" should become "1N4148"
        assert correct_ocr("IN4148") == "1N4148"

    def test_lm386_corruption(self):
        assert correct_ocr("LM3B6") == "LM386"

    def test_clean_text_unchanged(self):
        text = "TL072 LM386 2N3904 1N4148 BC547"
        assert correct_ocr(text) == text


# ---------------------------------------------------------------------------
# build_bom_entries — integration tests on realistic OCR snippets
# ---------------------------------------------------------------------------

class TestBuildBOMEntries:
    def _find(self, entries, category, value_contains):
        return [e for e in entries if e["category"] == category
                and value_contains.lower() in e["value"].lower()]

    def test_standard_resistors(self):
        text = "R1 10k  R2 47k  R3 100k  R4 1M"
        entries = build_bom_entries(text)
        values = {e["value"] for e in entries if e["category"] == "resistor"}
        assert "10k" in values
        assert "47k" in values
        assert "1M" in values

    def test_european_resistors(self):
        text = "4K7 1K5 2M2 100R"
        entries = build_bom_entries(text)
        values = {e["value"] for e in entries if e["category"] == "resistor"}
        assert "4.7k" in values
        assert "1.5k" in values
        assert "2.2M" in values

    def test_standard_capacitors(self):
        text = "C1 100nF  C2 47uF  C3 220pF  C4 10uF"
        entries = build_bom_entries(text)
        values = {e["value"] for e in entries if e["category"] == "capacitor"}
        assert "100nF" in values
        assert "47uF" in values
        assert "220pF" in values

    def test_european_capacitors(self):
        text = "4n7 coupling capacitor, 47u5 electrolytic"
        entries = build_bom_entries(text)
        values = {e["value"] for e in entries if e["category"] == "capacitor"}
        assert "4.7nF" in values

    def test_op_amp_ic(self):
        text = "U1 TL072CP dual op-amp, U2 LM386N audio amp"
        entries = build_bom_entries(text)
        ics = {e["value"] for e in entries if e["category"] == "ic"}
        assert "TL072CP" in ics or "TL072" in ics
        assert "LM386N" in ics or "LM386" in ics

    def test_xr2206_function_generator(self):
        text = "XR2206 function generator IC"
        entries = build_bom_entries(text)
        ics = {e["value"] for e in entries if e["category"] == "ic"}
        assert any("XR2206" in v for v in ics)

    def test_bbd_chips(self):
        text = "MN3207 BBD, MN3101 clock driver, PT2399 echo"
        entries = build_bom_entries(text)
        ics = {e["value"] for e in entries if e["category"] == "ic"}
        assert any("MN3207" in v for v in ics)
        assert any("PT2399" in v for v in ics)

    def test_transistors(self):
        text = "Q1 2N3904 NPN, Q2 BC547B, Q3 J201 JFET"
        entries = build_bom_entries(text)
        trans = {e["value"] for e in entries if e["category"] == "transistor"}
        assert "2N3904" in trans
        assert "BC547B" in trans
        assert "J201" in trans

    def test_diodes(self):
        text = "D1 1N4148, D2 1N34A germanium, D3 BAT41 schottky"
        entries = build_bom_entries(text)
        diodes = {e["value"] for e in entries if e["category"] == "diode"}
        assert "1N4148" in diodes
        assert "1N34A" in diodes
        assert "BAT41" in diodes

    def test_quantity_counting(self):
        # Three occurrences of 10k should yield quantity=3
        text = "R1 10k  R2 10k  R3 10k"
        entries = build_bom_entries(text)
        r10k = [e for e in entries if e["category"] == "resistor" and e["value"] == "10k"]
        assert len(r10k) == 1
        assert r10k[0]["quantity"] == 3

    def test_known_parts_switch(self):
        text = "true bypass with 3PDT stomp switch"
        entries = build_bom_entries(text)
        switches = [e for e in entries if e["category"] == "switch"]
        assert len(switches) >= 1

    def test_known_parts_jacks(self):
        text = "input jack 1/4 mono, output jack 1/4 mono, DC jack 2.1mm"
        entries = build_bom_entries(text)
        jacks = [e for e in entries if e["category"] == "jack"]
        assert len(jacks) >= 1

    def test_charge_pump_detection(self):
        text = "MAX1044 charge pump for negative rail"
        entries = build_bom_entries(text)
        ics = {e["value"] for e in entries if e["category"] == "ic"}
        assert "MAX1044" in ics

    def test_all_entries_have_required_keys(self):
        text = "R1 10k, C1 100nF, TL072, 2N3904, 1N4148"
        entries = build_bom_entries(text)
        for e in entries:
            assert "category" in e
            assert "value" in e
            assert "quantity" in e
            assert "source" in e
            assert e["source"] == "ocr"
            assert e["quantity"] >= 1

    def test_empty_text_returns_empty(self):
        assert build_bom_entries("") == []

    def test_no_false_positives_on_gibberish(self):
        # Pure noise should yield nothing or minimal false positives
        entries = build_bom_entries("xxxx yyyy zzzz 1234 aaaa")
        # Might get a bare number as resistor — but no ICs or transistors
        ics = [e for e in entries if e["category"] == "ic"]
        assert ics == []


# ---------------------------------------------------------------------------
# extract_voltages
# ---------------------------------------------------------------------------

class TestExtractVoltages:
    def test_positive_supply(self):
        volts = extract_voltages("+9V supply, +5V logic")
        assert any("9" in v for v in volts)

    def test_negative_rail(self):
        volts = extract_voltages("±15V regulated supply, -12V rail")
        assert any("15" in v for v in volts)

    def test_no_voltage_returns_empty(self):
        assert extract_voltages("R1 10k, C1 100nF") == []

    def test_capped_at_8(self):
        text = " ".join(f"+{v}V" for v in range(1, 20))
        volts = extract_voltages(text)
        assert len(volts) <= 8
