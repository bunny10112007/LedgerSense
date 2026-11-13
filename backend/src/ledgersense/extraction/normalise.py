from __future__ import annotations

import re

CORPORATE_SUFFIXES = {
    "pvt",
    "ltd",
    "llp",
    "co",
    "private",
    "limited",
    "inc",
    "corp",
    "corporation",
}


def compute_vendor_key(vendor_name: str | None, vendor_gstin: str | None) -> str:
    """Derive deterministic vendor_key from vendor_name and vendor_gstin.

    Format:
    - lowercase name
    - strip punctuation and common corporate suffixes (pvt, ltd, llp, co, private, limited)
    - collapse whitespace, slugify with hyphens
    - join with "|" + (vendor_gstin or "nogstin")
    """
    if not vendor_name:
        slug = "unknown"
    else:
        words = re.findall(r"[a-z0-9]+", vendor_name.lower())
        while words and words[-1] in CORPORATE_SUFFIXES:
            words.pop()
        slug = "-".join(words) if words else "unknown"

    gstin_part = vendor_gstin.strip().upper() if vendor_gstin and vendor_gstin.strip() else "nogstin"
    return f"{slug}|{gstin_part}"
