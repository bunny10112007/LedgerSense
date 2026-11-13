from __future__ import annotations

import json
import logging
import re
from decimal import Decimal
from typing import Any, Literal

from openai import OpenAIError
from pydantic import ValidationError
from sqlmodel import Session

from ledgersense.core.config import settings
from ledgersense.domain.models import ExtractedReceipt, Receipt
from ledgersense.llm.cache import CacheMissError, ExtractionCache
from ledgersense.llm.egress import log_outbound_call
from ledgersense.llm.kimi_provider import KimiProvider
from ledgersense.llm.pii import mask_pii
from ledgersense.llm.prompts import PROMPT_VERSION
from ledgersense.llm.provider import Provider, RawExtraction

logger = logging.getLogger(__name__)


def compute_vendor_key(vendor_name: str | None, vendor_gstin: str | None) -> str:
    """Derive deterministic vendor_key from vendor_name and vendor_gstin (Section 6.1)."""
    norm_name = re.sub(r"[^a-z0-9]+", "-", (vendor_name or "unknown").strip().lower()).strip("-")
    norm_gstin = (vendor_gstin or "").strip().upper()
    return f"{norm_name}|{norm_gstin}"


def check_receipt_arithmetic(receipt: ExtractedReceipt) -> list[str]:
    """Check arithmetic consistency of extracted subtotal, taxes, and total."""
    messages: list[str] = []
    if receipt.subtotal is not None and receipt.total is not None:
        calc_total = receipt.subtotal + receipt.cgst + receipt.sgst + receipt.igst
        if abs(calc_total - receipt.total) > Decimal("0.05"):
            messages.append(
                f"Arithmetic mismatch: subtotal ({receipt.subtotal}) + taxes ({receipt.cgst + receipt.sgst + receipt.igst}) "
                f"= {calc_total} != total ({receipt.total})"
            )
    return messages


def evaluate_confidence(receipt: ExtractedReceipt) -> Literal["OK", "LOW_CONFIDENCE"]:
    """Evaluate field confidences for key fields (vendor_gstin, invoice_date, total)."""
    for field in ("total", "invoice_date", "vendor_gstin"):
        conf = receipt.field_confidence.get(field)
        if conf is not None and conf < 0.70:
            return "LOW_CONFIDENCE"
    return "OK"


def parse_extracted_receipt(raw_json: str) -> tuple[ExtractedReceipt | None, str | None]:
    """Parse raw JSON into ExtractedReceipt or return error string."""
    try:
        return ExtractedReceipt.model_validate_json(raw_json), None
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        return None, str(exc)


class ReceiptExtractor:
    """Perception extraction orchestrator with caching, retry loop, egress logging, and validation."""

    def __init__(
        self,
        provider: Provider | None = None,
        cache: ExtractionCache | None = None,
    ) -> None:
        self.provider = provider or KimiProvider()
        self.cache = cache or ExtractionCache()

    def extract_document(
        self,
        file_bytes: bytes,
        mime: str = "image/png",
        run_id: str = "run:default",
        receipt_id: str | None = None,
        source_file: str = "unknown",
        hints: dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> Receipt:
        """Extract receipt metadata from document bytes with cache lookup, egress logging, and validation retry."""
        file_hash = ExtractionCache.compute_hash(file_bytes)
        rcpt_id = receipt_id or f"rcpt:{file_hash[:8]}"

        raw_extraction: RawExtraction | None = None

        # Step 1: Cache lookup
        try:
            raw_extraction = self.cache.get(
                file_bytes=file_bytes,
                model_id=self.provider.model_id,
                prompt_version=PROMPT_VERSION,
                session=session,
            )
        except CacheMissError:
            if settings.LLM_MODE == "replay":
                raise

        # Step 2: Live extraction on cache miss
        if raw_extraction is None:
            raw_extraction = self.provider.extract_receipt(
                image_bytes=file_bytes,
                mime=mime,
                hints=hints,
            )
            log_outbound_call(
                file_hash=file_hash,
                payload_bytes=file_bytes,
                model_id=self.provider.model_id,
                masked=False,
                run_id=run_id,
                session=session,
            )
            self.cache.put(
                file_bytes=file_bytes,
                model_id=self.provider.model_id,
                prompt_version=PROMPT_VERSION,
                raw_extraction=raw_extraction,
                session=session,
            )

        # Step 3: Parse and validate ExtractedReceipt with 1 retry on failure
        extracted, validation_error = parse_extracted_receipt(raw_extraction.raw_json)
        if validation_error:
            logger.warning("First extraction attempt validation failed for %s: %s", rcpt_id, validation_error)

        # Step 4: Retry ONCE if first attempt failed
        if extracted is None and validation_error is not None:
            if settings.LLM_MODE == "replay":
                logger.warning("Replay mode: cannot retry live extraction for %s", rcpt_id)
            else:
                try:
                    retry_extraction = self.provider.extract_receipt(
                        image_bytes=file_bytes,
                        mime=mime,
                        hints=hints,
                        error_feedback=validation_error,
                    )
                    log_outbound_call(
                        file_hash=file_hash,
                        payload_bytes=file_bytes,
                        model_id=self.provider.model_id,
                        masked=False,
                        run_id=run_id,
                        session=session,
                    )
                    extracted, retry_error = parse_extracted_receipt(retry_extraction.raw_json)
                    if extracted is not None:
                        self.cache.put(
                            file_bytes=file_bytes,
                            model_id=self.provider.model_id,
                            prompt_version=PROMPT_VERSION,
                            raw_extraction=retry_extraction,
                            session=session,
                        )
                    else:
                        validation_error = f"{validation_error} | Retry parse error: {retry_error}"
                except (OpenAIError, ValidationError, ValueError, json.JSONDecodeError, OSError) as retry_exc:
                    logger.warning("Second extraction attempt failed for %s: %s", rcpt_id, retry_exc)
                    validation_error = f"{validation_error} | Retry error: {retry_exc}"

        # Step 5: Construct Receipt
        if extracted is None:
            # Second failure: mark extraction_status = "FAILED", do NOT crash the batch
            return Receipt(
                id=rcpt_id,
                run_id=run_id,
                source_file=source_file,
                file_hash=file_hash,
                vendor_key="unknown|",
                doc_type="receipt",
                extraction_status="FAILED",
                check_messages=[f"Schema validation failed: {validation_error}"],
            )

        # Normal success
        vendor_key = compute_vendor_key(extracted.vendor_name, extracted.vendor_gstin)
        status = evaluate_confidence(extracted)
        arithmetic_messages = check_receipt_arithmetic(extracted)

        return Receipt(
            id=rcpt_id,
            run_id=run_id,
            source_file=source_file,
            file_hash=file_hash,
            vendor_key=vendor_key,
            extraction_status=status,
            check_messages=arithmetic_messages,
            doc_type=extracted.doc_type,
            vendor_name=extracted.vendor_name,
            vendor_gstin=extracted.vendor_gstin,
            invoice_no=extracted.invoice_no,
            invoice_date=extracted.invoice_date,
            line_items=extracted.line_items,
            subtotal=extracted.subtotal,
            cgst=extracted.cgst,
            sgst=extracted.sgst,
            igst=extracted.igst,
            total=extracted.total,
            payment_mode=extracted.payment_mode,
            field_confidence=extracted.field_confidence,
        )

    def extract_text(
        self,
        raw_text: str,
        run_id: str = "run:default",
        receipt_id: str | None = None,
        source_file: str = "unknown",
        hints: dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> Receipt:
        """Extract receipt from raw OCR text with PII masking, egress logging, and validation retry."""
        masked_text = mask_pii(raw_text)
        text_bytes = masked_text.encode("utf-8")
        file_hash = ExtractionCache.compute_hash(text_bytes)
        rcpt_id = receipt_id or f"rcpt:{file_hash[:8]}"

        raw_extraction: RawExtraction | None = None

        try:
            raw_extraction = self.cache.get(
                file_bytes=text_bytes,
                model_id=self.provider.model_id,
                prompt_version=PROMPT_VERSION,
                session=session,
            )
        except CacheMissError:
            if settings.LLM_MODE == "replay":
                raise

        if raw_extraction is None:
            raw_extraction = self.provider.structure_text(
                masked_text=masked_text,
                hints=hints,
            )
            log_outbound_call(
                file_hash=file_hash,
                payload_bytes=text_bytes,
                model_id=self.provider.model_id,
                masked=True,
                run_id=run_id,
                payload_raw=masked_text,
                session=session,
            )
            self.cache.put(
                file_bytes=text_bytes,
                model_id=self.provider.model_id,
                prompt_version=PROMPT_VERSION,
                raw_extraction=raw_extraction,
                session=session,
            )

        extracted, validation_error = parse_extracted_receipt(raw_extraction.raw_json)
        if validation_error:
            logger.warning("First text extraction attempt validation failed for %s: %s", rcpt_id, validation_error)

        if extracted is None and validation_error is not None:
            if settings.LLM_MODE == "replay":
                logger.warning("Replay mode: cannot retry text extraction for %s", rcpt_id)
            else:
                try:
                    retry_extraction = self.provider.structure_text(
                        masked_text=masked_text,
                        hints=hints,
                        error_feedback=validation_error,
                    )
                    log_outbound_call(
                        file_hash=file_hash,
                        payload_bytes=text_bytes,
                        model_id=self.provider.model_id,
                        masked=True,
                        run_id=run_id,
                        payload_raw=masked_text,
                        session=session,
                    )
                    extracted, retry_error = parse_extracted_receipt(retry_extraction.raw_json)
                    if extracted is not None:
                        self.cache.put(
                            file_bytes=text_bytes,
                            model_id=self.provider.model_id,
                            prompt_version=PROMPT_VERSION,
                            raw_extraction=retry_extraction,
                            session=session,
                        )
                    else:
                        validation_error = f"{validation_error} | Retry parse error: {retry_error}"
                except (OpenAIError, ValidationError, ValueError, json.JSONDecodeError, OSError) as retry_exc:
                    validation_error = f"{validation_error} | Retry error: {retry_exc}"

        if extracted is None:
            return Receipt(
                id=rcpt_id,
                run_id=run_id,
                source_file=source_file,
                file_hash=file_hash,
                vendor_key="unknown|",
                doc_type="receipt",
                extraction_status="FAILED",
                check_messages=[f"Schema validation failed: {validation_error}"],
            )

        vendor_key = compute_vendor_key(extracted.vendor_name, extracted.vendor_gstin)
        status = evaluate_confidence(extracted)
        arithmetic_messages = check_receipt_arithmetic(extracted)

        return Receipt(
            id=rcpt_id,
            run_id=run_id,
            source_file=source_file,
            file_hash=file_hash,
            vendor_key=vendor_key,
            extraction_status=status,
            check_messages=arithmetic_messages,
            doc_type=extracted.doc_type,
            vendor_name=extracted.vendor_name,
            vendor_gstin=extracted.vendor_gstin,
            invoice_no=extracted.invoice_no,
            invoice_date=extracted.invoice_date,
            line_items=extracted.line_items,
            subtotal=extracted.subtotal,
            cgst=extracted.cgst,
            sgst=extracted.sgst,
            igst=extracted.igst,
            total=extracted.total,
            payment_mode=extracted.payment_mode,
            field_confidence=extracted.field_confidence,
        )
