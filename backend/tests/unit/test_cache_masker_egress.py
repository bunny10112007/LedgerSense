from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest
from openai import RateLimitError
from sqlmodel import Session

from ledgersense.core.config import settings
from ledgersense.db.models import AuditEventRecord, EgressLogRecord
from ledgersense.db.session import engine, init_db
from ledgersense.extraction.extractor import ReceiptExtractor, compute_vendor_key
from ledgersense.llm.cache import CacheMissError, ExtractionCache
from ledgersense.llm.egress import log_outbound_call
from ledgersense.llm.kimi_provider import KimiProvider
from ledgersense.llm.pii import mask_pii
from ledgersense.llm.provider import RawExtraction


@pytest.fixture(autouse=True)
def setup_database() -> None:
    """Ensure database tables and triggers are created before unit tests."""
    init_db()


def test_mask_pii_preserves_gstin_and_masks_sensitive_data() -> None:
    """Test PII masking preserves 15-char GSTINs while masking PAN, Aadhaar, email, phone, and account."""
    raw_text = (
        "Vendor: Aravali Stationers\n"
        "GSTIN: 08AAAFA1234B1ZC\n"
        "PAN: AAAFA1234B\n"
        "Secondary GSTIN: 27AAPFU0939F1ZV\n"
        "Contact Email: accounts@aravali.co.in\n"
        "Mobile: +91 9876543210 or 8765432109\n"
        "Aadhaar Number: 4321-8765-1092 and 9876 5432 1098\n"
        "Bank Account No: 1234567890123456\n"
    )

    masked = mask_pii(raw_text)

    # CRITICAL INVARIANT: 15-character GSTINs must NEVER be masked
    assert "08AAAFA1234B1ZC" in masked
    assert "27AAPFU0939F1ZV" in masked

    # All sensitive PII must be masked
    assert "[MASKED_PAN]" in masked
    assert "[MASKED_EMAIL]" in masked
    assert "[MASKED_PHONE]" in masked
    assert "[MASKED_AADHAAR]" in masked
    assert "[MASKED_ACCOUNT]" in masked

    # Original sensitive strings must not appear
    assert "accounts@aravali.co.in" not in masked
    assert "9876543210" not in masked
    assert "8765432109" not in masked
    assert "4321-8765-1092" not in masked
    assert "1234567890123456" not in masked
    # Standalone PAN must not appear outside the GSTIN
    assert "PAN: AAAFA1234B" not in masked


def test_egress_and_audit_logging() -> None:
    """Outbound LLM calls must record one row in egress_log and one in audit_events."""
    test_hash = "abc123deadbeef456"
    test_bytes = b"sample receipt document bytes"

    with Session(engine) as session:
        egress_rec, audit_rec = log_outbound_call(
            file_hash=test_hash,
            payload_bytes=test_bytes,
            model_id="moonshot-v1-8k-vision-preview",
            masked=False,
            run_id="run:unit-test",
            session=session,
        )

        assert egress_rec.id.startswith("egress:")
        assert egress_rec.file_hash == test_hash
        assert egress_rec.bytes == len(test_bytes)
        assert egress_rec.model_id == "moonshot-v1-8k-vision-preview"
        assert egress_rec.masked is False

        assert audit_rec.id.startswith("evt:")
        assert audit_rec.actor == "system"
        assert audit_rec.action == "LLM_CALL"
        assert audit_rec.entity_id == test_hash
        assert audit_rec.payload_hash is not None

        # Verify persistence in database
        db_egress = session.get(EgressLogRecord, egress_rec.id)
        assert db_egress is not None
        assert db_egress.file_hash == test_hash

        db_audit = session.get(AuditEventRecord, audit_rec.id)
        assert db_audit is not None
        assert db_audit.action == "LLM_CALL"


def test_cache_miss_in_replay_mode_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """In replay mode, a cache miss must raise CacheMissError and never call provider."""
    monkeypatch.setattr(settings, "LLM_MODE", "replay")

    cache = ExtractionCache()
    dummy_bytes = b"unknown-document-bytes-for-miss-test"

    with pytest.raises(CacheMissError) as exc_info:
        cache.get(
            file_bytes=dummy_bytes,
            model_id="moonshot-v1-8k-vision-preview",
            prompt_version="v1",
        )
    assert "Cache miss in replay mode" in str(exc_info.value)


def test_cache_hit_returns_stored_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """ExtractionCache returns stored data from DB or filesystem."""
    cache = ExtractionCache()
    sample_bytes = b"known-document-bytes-sample"
    sample_json = json.dumps({"doc_type": "gst_invoice", "vendor_name": "Test Vendor", "total": "500.00"})

    raw_ext = RawExtraction(
        raw_json=sample_json,
        prompt_version="v1",
        model_id="moonshot-v1-8k-vision-preview",
        latency_ms=10,
    )

    with Session(engine) as session:
        cache.put(
            file_bytes=sample_bytes,
            model_id="moonshot-v1-8k-vision-preview",
            prompt_version="v1",
            raw_extraction=raw_ext,
            session=session,
        )

        hit = cache.get(
            file_bytes=sample_bytes,
            model_id="moonshot-v1-8k-vision-preview",
            prompt_version="v1",
            session=session,
        )

        assert hit is not None
        assert hit.raw_json == sample_json
        assert hit.model_id == "moonshot-v1-8k-vision-preview"


def test_extractor_cache_hit_zero_network_calls() -> None:
    """Cache hit returns stored RawExtraction with zero network calls to provider."""
    mock_provider = MagicMock()
    mock_provider.model_id = "moonshot-v1-8k-vision-preview"

    mock_cache = MagicMock()
    sample_json = json.dumps(
        {
            "doc_type": "gst_invoice",
            "vendor_name": "Aravali Stationers",
            "vendor_gstin": "08AAAFA1234B1ZC",
            "total": "11800.00",
            "payment_mode": "upi",
        }
    )
    mock_cache.get.return_value = RawExtraction(
        raw_json=sample_json,
        prompt_version="v1",
        model_id="moonshot-v1-8k-vision-preview",
        latency_ms=0,
    )

    extractor = ReceiptExtractor(provider=mock_provider, cache=mock_cache)
    test_bytes = b"already-cached-receipt-bytes"

    with Session(engine) as session:
        receipt = extractor.extract_document(test_bytes, source_file="cached.png", session=session)

        # Zero network calls to provider
        assert mock_provider.extract_receipt.call_count == 0
        assert receipt.extraction_status == "OK"
        assert receipt.vendor_name == "Aravali Stationers"
        assert receipt.vendor_key == "aravali-stationers|08AAAFA1234B1ZC"


def test_extractor_retry_loop_on_validation_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """On validation failure, extractor retries once with error feedback and succeeds if attempt 2 is valid."""
    monkeypatch.setattr(settings, "LLM_MODE", "live")

    # Mock provider: returns invalid JSON first, then valid ExtractedReceipt JSON on retry
    mock_provider = MagicMock()
    mock_provider.model_id = "moonshot-v1-8k-vision-preview"

    invalid_extraction = RawExtraction(
        raw_json='{"invalid_field": 123}',  # missing doc_type
        prompt_version="v1",
        model_id="moonshot-v1-8k-vision-preview",
        latency_ms=50,
    )
    valid_extraction = RawExtraction(
        raw_json=json.dumps(
            {
                "doc_type": "gst_invoice",
                "vendor_name": "Aravali Stationers",
                "vendor_gstin": "08AAAFA1234B1ZC",
                "total": "11800.00",
                "subtotal": "10000.00",
                "cgst": "900.00",
                "sgst": "900.00",
                "payment_mode": "upi",
                "field_confidence": {"total": 0.95, "vendor_gstin": 0.99},
            }
        ),
        prompt_version="v1",
        model_id="moonshot-v1-8k-vision-preview",
        latency_ms=45,
    )

    mock_provider.extract_receipt.side_effect = [invalid_extraction, valid_extraction]

    mock_cache = MagicMock()
    mock_cache.get.return_value = None  # Cache miss

    extractor = ReceiptExtractor(provider=mock_provider, cache=mock_cache)
    test_img = b"simulated-image-bytes"

    with Session(engine) as session:
        receipt = extractor.extract_document(test_img, source_file="g01.png", session=session)

        # Assert two calls were made (initial + retry)
        assert mock_provider.extract_receipt.call_count == 2
        # Verify retry call received error feedback
        _, kwargs = mock_provider.extract_receipt.call_args
        assert kwargs.get("error_feedback") is not None

        # Assert final status is OK
        assert receipt.extraction_status == "OK"
        assert receipt.vendor_name == "Aravali Stationers"
        assert receipt.vendor_key == "aravali-stationers|08AAAFA1234B1ZC"


def test_extractor_second_failure_marks_failed_without_crashing(monkeypatch: pytest.MonkeyPatch) -> None:
    """When second attempt also fails validation, extractor marks status FAILED and does not crash batch."""
    monkeypatch.setattr(settings, "LLM_MODE", "live")

    mock_provider = MagicMock()
    mock_provider.model_id = "moonshot-v1-8k-vision-preview"

    # Both calls return invalid json
    bad_extraction = RawExtraction(
        raw_json="This is not JSON at all",
        prompt_version="v1",
        model_id="moonshot-v1-8k-vision-preview",
        latency_ms=50,
    )
    mock_provider.extract_receipt.side_effect = [bad_extraction, bad_extraction]

    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    extractor = ReceiptExtractor(provider=mock_provider, cache=mock_cache)
    test_img = b"corrupted-receipt-image"

    with Session(engine) as session:
        receipt = extractor.extract_document(test_img, source_file="corrupted.png", session=session)

        # Extraction must not crash; status must be FAILED
        assert receipt.extraction_status == "FAILED"
        assert len(receipt.check_messages) > 0
        assert "Schema validation failed" in receipt.check_messages[0]
        assert receipt.source_file == "corrupted.png"


def test_vendor_key_deterministic_formatting() -> None:
    """Test compute_vendor_key formats lowercase alphanumeric + dash and uppercase GSTIN."""
    assert compute_vendor_key("Aravali Stationers", "08AAAFA1234B1ZC") == "aravali-stationers|08AAAFA1234B1ZC"
    assert compute_vendor_key("Pink  City   Fuels", "08aaacp5678c1zd") == "pink-city-fuels|08AAACP5678C1ZD"
    assert compute_vendor_key("Local Tea Stall", None) == "local-tea-stall|"
    assert compute_vendor_key(None, None) == "unknown|"


def test_kimi_provider_backoff_retry_on_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """KimiProvider retries with exponential backoff on HTTP 429 RateLimitError."""
    monkeypatch.setattr("time.sleep", lambda s: None)

    call_count = 0

    def mock_chat_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RateLimitError(
                message="Rate limit exceeded",
                response=httpx.Response(
                    429, request=httpx.Request("POST", "https://api.moonshot.cn/v1/chat/completions")
                ),
                body={"error": "Rate limit"},
            )
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps({"doc_type": "receipt"})))]
        mock_resp.usage = MagicMock(prompt_tokens=50, completion_tokens=25)
        return mock_resp

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = mock_chat_create

    provider = KimiProvider(client=mock_client)
    res = provider.extract_receipt(b"fake-bytes")

    assert call_count == 3
    assert res.raw_json == json.dumps({"doc_type": "receipt"})


def test_kimi_provider_semaphore_concurrency() -> None:
    """Verify semaphore of 4 limits in-flight requests."""
    provider = KimiProvider(client=MagicMock())
    assert provider.semaphore._value == 4

