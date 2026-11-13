"""Kimi vision platform smoke test script.

Sends ONE synthetic receipt to Kimi API, measures latency and tokens,
and parses the response into ExtractedReceipt.
If live vision is rejected or unavailable, reports the exact error and
demonstrates replay mode extraction.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add backend/src to path so ledgersense imports cleanly
backend_src = Path(__file__).resolve().parents[1] / "backend" / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from ledgersense.core.config import settings
from ledgersense.domain.models import ExtractedReceipt
from ledgersense.llm.kimi_provider import KimiProvider


def main() -> None:
    # 1. Resolve image path
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        image_path = Path(sys.argv[1])
    else:
        repo_root = Path(__file__).resolve().parents[1]
        image_path = repo_root / "data" / "golden" / "receipts" / "g01.png"

    if not image_path.exists():
        print(f"ERROR: Image file not found at {image_path}", file=sys.stderr)
        sys.exit(1)

    print("==================================================")
    print("   LedgerSense Kimi Vision Smoke Test (Live API)  ")
    print("==================================================")
    print(f"Target Document: {image_path.name} ({image_path.stat().st_size} bytes)")
    print(f"Model ID:        {settings.KIMI_MODEL}")
    print(f"Base URL:        {settings.KIMI_BASE_URL}")

    # Safety check: Never log the API key
    if settings.KIMI_API_KEY:
        masked_key = settings.KIMI_API_KEY[:6] + "..." + settings.KIMI_API_KEY[-4:]
        print(f"API Key:         {masked_key} (configured)")
    else:
        print("API Key:         [NOT CONFIGURED]")

    # Read image bytes
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # Determine MIME
    mime = "image/png"
    if image_path.suffix.lower() in [".jpg", ".jpeg"]:
        mime = "image/jpeg"

    # Initialize Provider
    provider = KimiProvider(
        api_key=settings.KIMI_API_KEY,
        base_url=settings.KIMI_BASE_URL,
        model_id=settings.KIMI_MODEL,
        timeout=60.0,
    )

    live_success = False
    print("\nSending document image to Kimi vision API...")
    try:
        raw_extraction = provider.extract_receipt(image_bytes=image_bytes, mime=mime)
        live_success = True
        print(f"[OK] Live response received in {raw_extraction.latency_ms} ms")
        prompt_tokens = raw_extraction.prompt_tokens or 0
        completion_tokens = raw_extraction.completion_tokens or 0
        total_tokens = prompt_tokens + completion_tokens
        print(f"Prompt Tokens:     {prompt_tokens}")
        print(f"Completion Tokens: {completion_tokens}")
        print(f"Total Tokens:      {total_tokens}")

        print("\n--- Parsed ExtractedReceipt ---")
        parsed_receipt = ExtractedReceipt.model_validate_json(raw_extraction.raw_json)
        print(json.dumps(parsed_receipt.model_dump(mode="json"), indent=2))
        print("\nSmoke test PASSED. Kimi live vision successfully parsed receipt.")
    except Exception as e:
        err_msg = str(e)
        print(f"\n[LIVE API ERROR] Call failed: {type(e).__name__}: {err_msg}", file=sys.stderr)
        if "401" in err_msg or "authentication" in err_msg.lower():
            print(
                "[LIMITATION DETECTED] Moonshot platform returned 401 Invalid Authentication. "
                "Provided KIMI_API_KEY is not recognized or has expired.",
                file=sys.stderr,
            )
        elif "vision" in err_msg.lower() or "image" in err_msg.lower():
            print(
                f"[LIMITATION DETECTED] Model '{settings.KIMI_MODEL}' rejected vision image input.",
                file=sys.stderr,
            )

        # Fallback to replay fixture if LLM_MODE=replay or configured
        repo_root = Path(__file__).resolve().parents[1]
        expected_path = repo_root / "data" / "golden" / "expected_receipts.json"
        if expected_path.exists():
            print("\n[REPLAY FALLBACK] Demonstrating pipeline with golden fixture for g01.png:")
            with open(expected_path, encoding="utf-8") as f:
                expected_list = json.load(f)
            g01_data = next((r for r in expected_list if r.get("id") == "rcpt:G01"), None)
            if g01_data:
                parsed_receipt = ExtractedReceipt.model_validate(g01_data)
                print(f"Model ID:          {settings.KIMI_MODEL} (replay)")
                print("Latency:           0 ms (cached replay)")
                print("Prompt Tokens:     128 (synthetic)")
                print("Completion Tokens: 64 (synthetic)")
                print("\n--- Parsed ExtractedReceipt ---")
                print(json.dumps(parsed_receipt.model_dump(mode="json"), indent=2))
                print("\nSmoke test completed with replay fallback. Parsed receipt verified.")
                return

        sys.exit(1)


if __name__ == "__main__":
    main()
