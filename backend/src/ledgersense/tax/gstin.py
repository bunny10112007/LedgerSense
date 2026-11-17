from __future__ import annotations

import re

from ledgersense.domain.models import GstinResult

CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Valid 2-digit Indian GST state / UT codes:
# 01-38: Standard states & union territories
# 97: Other Territory
# 99: Centre Jurisdiction
VALID_STATE_CODES: frozenset[str] = frozenset(
    {f"{i:02d}" for i in range(1, 39)} | {"97", "99"}
)

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
ENTITY_CODE_PATTERN = re.compile(r"^[1-9A-Z]$")


def compute_gstin_check_char(first_14_chars: str) -> str:
    """Compute the 15th character mod-36 checksum over the first 14 characters."""
    total = 0
    for i, ch in enumerate(first_14_chars[:14]):
        factor = 2 if (i % 2 == 1) else 1
        prod = CHARS.index(ch) * factor
        total += (prod // 36) + (prod % 36)
    return CHARS[(36 - (total % 36)) % 36]


def validate_gstin(value: str) -> GstinResult:
    """Validate a 15-character Indian Goods and Services Tax Identification Number (GSTIN).

    Validates format, state code, PAN structure, default character, and mod-36 check character.
    Returns GstinResult(ok=..., reason=..., expected_check_char=...).
    """
    if not isinstance(value, str) or len(value) != 15:
        return GstinResult(ok=False, reason="invalid_length", expected_check_char=None)

    if any(c.islower() for c in value):
        return GstinResult(ok=False, reason="lowercase_not_allowed", expected_check_char=None)

    state_code = value[0:2]
    if state_code not in VALID_STATE_CODES:
        return GstinResult(ok=False, reason="invalid_state_code", expected_check_char=None)

    pan_part = value[2:12]
    if not PAN_PATTERN.match(pan_part):
        return GstinResult(ok=False, reason="invalid_pan_format", expected_check_char=None)

    entity_code = value[12]
    if not ENTITY_CODE_PATTERN.match(entity_code):
        return GstinResult(ok=False, reason="invalid_entity_code", expected_check_char=None)

    default_char = value[13]
    if default_char != "Z":
        return GstinResult(ok=False, reason="invalid_default_char", expected_check_char=None)

    expected = compute_gstin_check_char(value[:14])
    if value[14] != expected:
        return GstinResult(ok=False, reason="checksum_mismatch", expected_check_char=expected)

    return GstinResult(ok=True, reason=None, expected_check_char=expected)
