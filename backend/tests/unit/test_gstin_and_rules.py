from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ledgersense.tax.gstin import validate_gstin
from ledgersense.tax.rules_engine import (
    RuleSet,
    derive_regime,
    load_rules,
    resolve_legal_ref,
)

# --- GSTIN Validation Tests ---


def test_gstin_valid_examples() -> None:
    res1 = validate_gstin("27AAPFU0939F1ZV")
    assert res1.ok is True
    assert res1.reason is None
    assert res1.expected_check_char == "V"

    res2 = validate_gstin("29AAGCB7383J1Z4")
    assert res2.ok is True
    assert res2.reason is None
    assert res2.expected_check_char == "4"


def test_gstin_checksum_mismatch() -> None:
    res = validate_gstin("27AAPFU0939F1ZX")
    assert res.ok is False
    assert res.reason == "checksum_mismatch"
    assert res.expected_check_char == "V"


def test_gstin_format_valid_checksum_invalid() -> None:
    # 06BZAHM6385P6Z2 has valid syntax but checksum character is '0', not '2'
    res = validate_gstin("06BZAHM6385P6Z2")
    assert res.ok is False
    assert res.reason == "checksum_mismatch"
    assert res.expected_check_char == "0"


def test_gstin_invalid_length() -> None:
    assert validate_gstin("27AAPFU0939F1Z").ok is False
    assert validate_gstin("27AAPFU0939F1Z").reason == "invalid_length"

    assert validate_gstin("27AAPFU0939F1ZVV").ok is False
    assert validate_gstin("27AAPFU0939F1ZVV").reason == "invalid_length"

    assert validate_gstin("").ok is False
    assert validate_gstin("").reason == "invalid_length"


def test_gstin_lowercase_not_allowed() -> None:
    res1 = validate_gstin("27aapfu0939f1zv")
    assert res1.ok is False
    assert res1.reason == "lowercase_not_allowed"

    res2 = validate_gstin("27AAPFU0939f1ZV")
    assert res2.ok is False
    assert res2.reason == "lowercase_not_allowed"


def test_gstin_invalid_state_codes() -> None:
    # 00 is not a valid state code
    res0 = validate_gstin("00AAPFU0939F1ZV")
    assert res0.ok is False
    assert res0.reason == "invalid_state_code"

    # 90 is not a valid state code
    res90 = validate_gstin("90AAPFU0939F1ZV")
    assert res90.ok is False
    assert res90.reason == "invalid_state_code"

    # 39 is not a valid state code (valid are 01..38, 97, 99)
    res39 = validate_gstin("39AAPFU0939F1ZV")
    assert res39.ok is False
    assert res39.reason == "invalid_state_code"


def test_gstin_invalid_pan_format() -> None:
    # Bad PAN letters
    res1 = validate_gstin("27123450939F1ZV")
    assert res1.ok is False
    assert res1.reason == "invalid_pan_format"

    # Digits in first 5 of PAN
    res2 = validate_gstin("27AAP1U0939F1ZV")
    assert res2.ok is False
    assert res2.reason == "invalid_pan_format"


def test_gstin_invalid_entity_code() -> None:
    # 13th char cannot be '0' or special char
    res = validate_gstin("27AAPFU0939F0ZV")
    assert res.ok is False
    assert res.reason == "invalid_entity_code"


def test_gstin_invalid_default_char() -> None:
    # 14th char must be 'Z'
    res = validate_gstin("27AAPFU0939F1AV")
    assert res.ok is False
    assert res.reason == "invalid_default_char"


def test_golden_gstins() -> None:
    valid_golden = [
        ("08AAAFA1234B1ZC", "C"),
        ("08AAACP5678C1ZD", "D"),
        ("29AABCC2345D1Z1", "1"),
        ("08AABFS3456E1ZB", "B"),
        ("08AAACQ4567F1ZC", "C"),
        ("27AAACS5678G1Z2", "2"),
        ("08AAAFS8901K1ZZ", "Z"),
        ("29AAACD9012L1ZI", "I"),
    ]
    for gstin, expected_char in valid_golden:
        res = validate_gstin(gstin)
        assert res.ok is True, f"Expected {gstin} to be valid, got {res}"
        assert res.reason is None
        assert res.expected_check_char == expected_char

    # Golden receipt G10 has an invalid checksum character ('X' instead of 'U')
    g10_res = validate_gstin("08AAAFM6789H1ZX")
    assert g10_res.ok is False
    assert g10_res.reason == "checksum_mismatch"
    assert g10_res.expected_check_char == "U"


# --- Rules Engine & Statutory Mapping Tests ---


def test_load_rules_structure() -> None:
    rules = load_rules()
    assert isinstance(rules, RuleSet)

    # Check GST rules
    assert rules.gst.version == 1
    assert len(rules.gst.categories) == 3
    cat_ids = [c.id for c in rules.gst.categories]
    assert "FOOD_BEVERAGE" in cat_ids
    assert "MOTOR_VEHICLE" in cat_ids
    assert "HEALTH_CLUB" in cat_ids

    # Check IT rules
    assert rules.it.version == 1
    assert rules.it.financial_year == "2025-26"
    assert rules.it.cash_expense_limit.amount == Decimal("10000.00")
    assert len(rules.it.deductions) == 2


def test_unverified_rules_badges() -> None:
    rules = load_rules()
    assert rules.is_gst_verified is False
    assert rules.is_it_verified is False
    assert rules.gst.verified_by is None
    assert rules.it.verified_by is None


def test_regime_boundary_derivation() -> None:
    assert derive_regime(date(2025, 4, 1)) == "ITA_1961"
    assert derive_regime(date(2026, 3, 31)) == "ITA_1961"
    assert derive_regime(date(2026, 4, 1)) == "ITA_2025"
    assert derive_regime(date(2027, 3, 31)) == "ITA_2025"


def test_resolve_legal_ref_and_fallbacks() -> None:
    assert resolve_legal_ref("s.80C", "s.123", "ITA_1961") == "s.80C"
    assert resolve_legal_ref("s.80C", "s.123", "ITA_2025") == "s.123"

    # Pending mapping fallback to "mapping pending"
    assert resolve_legal_ref("s.40A(3)", None, "ITA_1961") == "s.40A(3)"
    assert resolve_legal_ref("s.40A(3)", None, "ITA_2025") == "mapping pending"


def test_cash_limit_and_deduction_refs() -> None:
    rules = load_rules()

    # Cash limit: 1961 has s.40A(3), 2025 is None => mapping pending
    assert rules.cash_limit_ref("ITA_1961") == "s.40A(3)"
    assert rules.cash_limit_ref("ITA_2025") == "mapping pending"

    # 80C: s.80C vs s.123
    assert rules.deduction_ref("80C", "ITA_1961") == "s.80C"
    assert rules.deduction_ref("80C", "ITA_2025") == "s.123"

    # 80D: s.80D vs s.126
    assert rules.deduction_ref("80D", "ITA_1961") == "s.80D"
    assert rules.deduction_ref("80D", "ITA_2025") == "s.126"

    with pytest.raises(ValueError, match="Deduction section '80G' not found"):
        rules.deduction_ref("80G", "ITA_1961")
