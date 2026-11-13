from __future__ import annotations

import re

# 15-character Indian GSTIN pattern:
# 2-digit state code + 10-char PAN ([A-Z]{5}[0-9]{4}[A-Z]) + 1 entity char + 'Z' + 1 check char
GSTIN_PATTERN = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")

# PII Patterns to mask:
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# 12-digit Aadhaar / Indian ID (formatted with spaces/hyphens or continuous)
AADHAAR_PATTERN = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")
# Indian mobile numbers: 10 digits starting with 6, 7, 8, or 9 (with optional +91 prefix)
PHONE_PATTERN = re.compile(r"(?:\+91[-\s]?)?\b[6-9]\d{9}\b")
# Bank account numbers: 9 to 18 continuous digits
ACCOUNT_PATTERN = re.compile(r"\b\d{9,18}\b")
# Indian PAN: 5 uppercase letters, 4 digits, 1 uppercase letter
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")


def mask_pii(text: str) -> str:
    """Mask sensitive PII (PAN, Aadhaar, phone, email, bank account numbers).

    CRITICAL INVARIANT:
    Never mask a 15-character GSTIN, even though characters 3-12 form a valid PAN substring.
    """
    if not text:
        return text

    # Step 1: Extract and preserve all valid 15-char GSTINs with safe placeholder tokens
    preserved_gstins: dict[str, str] = {}

    def preserve_gstin(match: re.Match[str]) -> str:
        token = f"__PRESERVED_GSTIN_{len(preserved_gstins)}__"
        preserved_gstins[token] = match.group(0)
        return token

    masked = GSTIN_PATTERN.sub(preserve_gstin, text)

    # Step 2: Mask Email addresses
    masked = EMAIL_PATTERN.sub("[MASKED_EMAIL]", masked)

    # Step 3: Mask formatted 12-digit Aadhaar IDs
    masked = AADHAAR_PATTERN.sub("[MASKED_AADHAAR]", masked)

    # Step 4: Mask Indian Mobile Numbers
    masked = PHONE_PATTERN.sub("[MASKED_PHONE]", masked)

    # Step 5: Mask Long Bank Account Numbers (9 to 18 digits)
    masked = ACCOUNT_PATTERN.sub("[MASKED_ACCOUNT]", masked)

    # Step 6: Mask Standalone 10-char PANs
    masked = PAN_PATTERN.sub("[MASKED_PAN]", masked)

    # Step 7: Restore all preserved GSTINs exactly as original
    for token, original_gstin in preserved_gstins.items():
        masked = masked.replace(token, original_gstin)

    return masked
