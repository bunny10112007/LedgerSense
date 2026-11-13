import json
from decimal import Decimal

import httpx
from openai import OpenAI

from ledgersense.domain.models import ExtractedReceipt
from ledgersense.llm.kimi_provider import KimiProvider
from ledgersense.llm.provider import Provider, RawExtraction


def create_mock_client(payload_dict: dict) -> OpenAI:
    """Create an OpenAI client backed by a mock HTTP transport to guarantee zero network calls."""

    def handler(request: httpx.Request) -> httpx.Response:
        req_body = json.loads(request.content.decode("utf-8"))
        assert "messages" in req_body
        assert req_body["response_format"] == {"type": "json_object"}

        response_payload = {
            "id": "chatcmpl-mock-123",
            "object": "chat.completion",
            "created": 1700000000,
            "model": req_body.get("model", "moonshot-v1-8k-vision-preview"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(payload_dict),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 128,
                "completion_tokens": 64,
                "total_tokens": 192,
            },
        }
        return httpx.Response(200, json=response_payload)

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return OpenAI(
        api_key="mock-api-key-never-sent",
        base_url="https://mock.moonshot.cn/v1",
        http_client=http_client,
    )


def test_kimi_provider_satisfies_protocol():
    mock_client = create_mock_client({"doc_type": "receipt"})
    provider = KimiProvider(client=mock_client)
    assert isinstance(provider, Provider)
    assert provider.model_id == "moonshot-v1-8k-vision-preview"


def test_kimi_provider_extract_receipt_mock_transport():
    sample_json = {
        "doc_type": "gst_invoice",
        "vendor_name": "Aravali Stationers",
        "vendor_gstin": "08AAAFA1234B1ZC",
        "invoice_no": "INV-2041",
        "invoice_date": "2025-06-12",
        "line_items": [
            {
                "description": "Office stationery and printing paper",
                "quantity": "1",
                "unit_price": "10000.00",
                "amount": "10000.00",
                "hsn_sac": "4817",
                "tax_rate_pct": "18.00",
            }
        ],
        "subtotal": "10000.00",
        "cgst": "900.00",
        "sgst": "900.00",
        "igst": "0.00",
        "total": "11800.00",
        "payment_mode": "upi",
        "field_confidence": {
            "vendor_gstin": 0.99,
            "invoice_date": 0.98,
            "total": 0.99,
        },
    }

    mock_client = create_mock_client(sample_json)
    provider = KimiProvider(client=mock_client)

    dummy_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRdummyimagebytes"
    extraction = provider.extract_receipt(dummy_image_bytes, mime="image/png")

    assert isinstance(extraction, RawExtraction)
    assert extraction.model_id == "moonshot-v1-8k-vision-preview"
    assert extraction.prompt_version == "v1"
    assert extraction.prompt_tokens == 128
    assert extraction.completion_tokens == 64
    assert extraction.latency_ms >= 0

    # Parse raw json to ExtractedReceipt model
    parsed = ExtractedReceipt.model_validate_json(extraction.raw_json)
    assert parsed.vendor_name == "Aravali Stationers"
    assert parsed.vendor_gstin == "08AAAFA1234B1ZC"
    assert parsed.total == Decimal("11800.00")
    assert parsed.payment_mode == "upi"


def test_kimi_provider_structure_text_mock_transport():
    sample_json = {
        "doc_type": "fare",
        "vendor_name": "QuickCab Mobility",
        "vendor_gstin": "08AAACQ4567F1ZC",
        "invoice_no": "RCP-5529",
        "invoice_date": "2025-10-06",
        "total": "640.00",
        "payment_mode": "upi",
    }

    mock_client = create_mock_client(sample_json)
    provider = KimiProvider(client=mock_client)

    extraction = provider.structure_text("Cab trip receipt RCP-5529 INR 640.00")
    assert isinstance(extraction, RawExtraction)
    parsed = ExtractedReceipt.model_validate_json(extraction.raw_json)
    assert parsed.doc_type == "fare"
    assert parsed.total == Decimal("640.00")
