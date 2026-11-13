from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from openai import OpenAIError
from pydantic import ValidationError
from sqlmodel import Session

from ledgersense.core.config import settings
from ledgersense.domain.models import ExtractedReceipt, Receipt
from ledgersense.extraction.checks import (
    evaluate_confidence_status,
    run_arithmetic_checks,
)
from ledgersense.extraction.normalise import compute_vendor_key
from ledgersense.llm.cache import CacheMissError, ExtractionCache
from ledgersense.llm.egress import log_outbound_call
from ledgersense.llm.kimi_provider import KimiProvider
from ledgersense.llm.pii import mask_pii
from ledgersense.llm.prompts import PROMPT_VERSION
from ledgersense.llm.provider import Provider, RawExtraction

logger = logging.getLogger(__name__)


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
        path: Path | str | bytes | None = None,
        file_bytes: bytes | None = None,
        provider: Provider | None = None,
        cache: ExtractionCache | None = None,
        mime: str = "image/png",
        run_id: str = "run:default",
        receipt_id: str | None = None,
        source_file: str = "unknown",
        hints: dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> Receipt:
        """Extract receipt metadata from document path or bytes with cache lookup, egress logging, and retry."""
        active_provider = provider or self.provider
        active_cache = cache or self.cache

        # Resolve payload bytes
        if path is not None:
            if isinstance(path, (str, Path)):
                path_obj = Path(path)
                data_bytes = path_obj.read_bytes()
                if source_file == "unknown":
                    source_file = str(path)
            elif isinstance(path, bytes):
                data_bytes = path
            else:
                raise TypeError(f"Unsupported path type: {type(path)}")
        elif file_bytes is not None:
            data_bytes = file_bytes
        else:
            raise ValueError("Either path or file_bytes must be provided")

        file_hash = ExtractionCache.compute_hash(data_bytes)
        rcpt_id = receipt_id or f"rcpt:{file_hash[:8]}"

        raw_extraction: RawExtraction | None = None

        # Step 1: Cache lookup
        try:
            raw_extraction = active_cache.get(
                file_bytes=data_bytes,
                model_id=active_provider.model_id,
                prompt_version=PROMPT_VERSION,
                session=session,
            )
        except CacheMissError:
            if settings.LLM_MODE == "replay":
                raise

        # Step 2: Live extraction on cache miss
        if raw_extraction is None:
            raw_extraction = active_provider.extract_receipt(
                image_bytes=data_bytes,
                mime=mime,
                hints=hints,
            )
            log_outbound_call(
                file_hash=file_hash,
                payload_bytes=data_bytes,
                model_id=active_provider.model_id,
                masked=False,
                run_id=run_id,
                session=session,
            )
            active_cache.put(
                file_bytes=data_bytes,
                model_id=active_provider.model_id,
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
                    retry_extraction = active_provider.extract_receipt(
                        image_bytes=data_bytes,
                        mime=mime,
                        hints=hints,
                        error_feedback=validation_error,
                    )
                    log_outbound_call(
                        file_hash=file_hash,
                        payload_bytes=data_bytes,
                        model_id=active_provider.model_id,
                        masked=False,
                        run_id=run_id,
                        session=session,
                    )
                    extracted, retry_error = parse_extracted_receipt(retry_extraction.raw_json)
                    if extracted is not None:
                        active_cache.put(
                            file_bytes=data_bytes,
                            model_id=active_provider.model_id,
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
                vendor_key="unknown|nogstin",
                doc_type="receipt",
                extraction_status="FAILED",
                check_messages=[f"Schema validation failed: {validation_error}"],
            )

        # Normal success: compute normalised vendor_key and run arithmetic/confidence checks
        vendor_key = compute_vendor_key(extracted.vendor_name, extracted.vendor_gstin)
        status, conf_warnings = evaluate_confidence_status(extracted)
        arithmetic_messages = run_arithmetic_checks(extracted)
        all_check_messages = arithmetic_messages + conf_warnings

        return Receipt(
            id=rcpt_id,
            run_id=run_id,
            source_file=source_file,
            file_hash=file_hash,
            vendor_key=vendor_key,
            extraction_status=status,
            check_messages=all_check_messages,
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
        provider: Provider | None = None,
        cache: ExtractionCache | None = None,
        run_id: str = "run:default",
        receipt_id: str | None = None,
        source_file: str = "unknown",
        hints: dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> Receipt:
        """Extract receipt from raw OCR text with PII masking, egress logging, and validation retry."""
        active_provider = provider or self.provider
        active_cache = cache or self.cache

        masked_text = mask_pii(raw_text)
        text_bytes = masked_text.encode()
        file_hash = ExtractionCache.compute_hash(text_bytes)
        rcpt_id = receipt_id or f"rcpt:{file_hash[:8]}"

        raw_extraction: RawExtraction | None = None

        try:
            raw_extraction = active_cache.get(
                file_bytes=text_bytes,
                model_id=active_provider.model_id,
                prompt_version=PROMPT_VERSION,
                session=session,
            )
        except CacheMissError:
            if settings.LLM_MODE == "replay":
                raise

        if raw_extraction is None:
            raw_extraction = active_provider.structure_text(
                masked_text=masked_text,
                hints=hints,
            )
            log_outbound_call(
                file_hash=file_hash,
                payload_bytes=text_bytes,
                model_id=active_provider.model_id,
                masked=True,
                run_id=run_id,
                payload_raw=masked_text,
                session=session,
            )
            active_cache.put(
                file_bytes=text_bytes,
                model_id=active_provider.model_id,
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
                    retry_extraction = active_provider.structure_text(
                        masked_text=masked_text,
                        hints=hints,
                        error_feedback=validation_error,
                    )
                    log_outbound_call(
                        file_hash=file_hash,
                        payload_bytes=text_bytes,
                        model_id=active_provider.model_id,
                        masked=True,
                        run_id=run_id,
                        payload_raw=masked_text,
                        session=session,
                    )
                    extracted, retry_error = parse_extracted_receipt(retry_extraction.raw_json)
                    if extracted is not None:
                        active_cache.put(
                            file_bytes=text_bytes,
                            model_id=active_provider.model_id,
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
                vendor_key="unknown|nogstin",
                doc_type="receipt",
                extraction_status="FAILED",
                check_messages=[f"Schema validation failed: {validation_error}"],
            )

        vendor_key = compute_vendor_key(extracted.vendor_name, extracted.vendor_gstin)
        status, conf_warnings = evaluate_confidence_status(extracted)
        arithmetic_messages = run_arithmetic_checks(extracted)
        all_check_messages = arithmetic_messages + conf_warnings

        return Receipt(
            id=rcpt_id,
            run_id=run_id,
            source_file=source_file,
            file_hash=file_hash,
            vendor_key=vendor_key,
            extraction_status=status,
            check_messages=all_check_messages,
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
