from __future__ import annotations

from decimal import Decimal
from typing import Literal

from ledgersense.domain.models import ExtractedReceipt


def run_arithmetic_checks(receipt: ExtractedReceipt) -> list[str]:
    """Verify arithmetic cross-checks on extracted receipt data.

    1. sum(line_items.amount) == subtotal (when line_items and subtotal present)
    2. subtotal + cgst + sgst + igst == total (when subtotal and total present)
    3. cgst == sgst when intra-state (cgst > 0 or sgst > 0)
    """
    messages: list[str] = []

    # 1. Line items total vs subtotal
    if receipt.line_items and receipt.subtotal is not None:
        line_sum = sum(item.amount for item in receipt.line_items)
        if abs(line_sum - receipt.subtotal) > Decimal("0.05"):
            messages.append(
                f"Line items total ({line_sum}) does not match subtotal ({receipt.subtotal})"
            )

    # 2. Subtotal + taxes vs total
    if receipt.subtotal is not None and receipt.total is not None:
        calc_total = receipt.subtotal + receipt.cgst + receipt.sgst + receipt.igst
        if abs(calc_total - receipt.total) > Decimal("0.05"):
            messages.append(
                f"Subtotal ({receipt.subtotal}) + taxes ({receipt.cgst + receipt.sgst + receipt.igst}) "
                f"= {calc_total} does not match total ({receipt.total})"
            )

    # 3. Intra-state CGST == SGST
    if (receipt.cgst > Decimal("0.00") or receipt.sgst > Decimal("0.00")) and abs(receipt.cgst - receipt.sgst) > Decimal("0.05"):
        messages.append(
            f"Intra-state GST mismatch: CGST ({receipt.cgst}) does not match SGST ({receipt.sgst})"
        )

    return messages


def evaluate_confidence_status(
    receipt: ExtractedReceipt,
    threshold: float = 0.80,
) -> tuple[Literal["OK", "LOW_CONFIDENCE"], list[str]]:
    """Check key field confidences (vendor_gstin, invoice_date, total).

    If any key field has confidence < threshold (default 0.80), set extraction_status = 'LOW_CONFIDENCE'.
    """
    warnings: list[str] = []
    status: Literal["OK", "LOW_CONFIDENCE"] = "OK"

    if receipt.field_confidence:
        for field in ("vendor_gstin", "invoice_date", "total"):
            conf = receipt.field_confidence.get(field)
            if conf is not None and conf < threshold:
                status = "LOW_CONFIDENCE"
                warnings.append(f"Low confidence on {field}: {conf:.2f} < {threshold:.2f}")

    return status, warnings
