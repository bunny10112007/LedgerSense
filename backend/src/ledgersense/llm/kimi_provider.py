import base64
import time
from typing import Any

from openai import OpenAI

from ledgersense.core.config import settings
from ledgersense.llm.prompts import PROMPT_VERSION, get_extraction_system_prompt
from ledgersense.llm.provider import RawExtraction


class KimiProvider:
    """Vision and text perception provider using Kimi (Moonshot) via OpenAI-compatible SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_id: str | None = None,
        timeout: float = 60.0,
        client: OpenAI | None = None,
    ) -> None:
        self.model_id = model_id or settings.KIMI_MODEL
        self.base_url = base_url or settings.KIMI_BASE_URL
        self.api_key = api_key or settings.KIMI_API_KEY
        self.timeout = timeout

        if client is not None:
            self.client = client
        else:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )

    def extract_receipt(
        self,
        image_bytes: bytes,
        mime: str = "image/png",
        hints: dict[str, Any] | None = None,
    ) -> RawExtraction:
        """Send receipt image to Kimi vision model and return structured RawExtraction."""
        b64_image = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime};base64,{b64_image}"

        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": "Extract all fields from this document into the required JSON schema.",
            },
            {
                "type": "image_url",
                "image_url": {"url": data_url},
            },
        ]
        if hints:
            user_content.append({"type": "text", "text": f"Context hints: {hints}"})

        messages = [
            {"role": "system", "content": get_extraction_system_prompt()},
            {"role": "user", "content": user_content},
        ]

        start_time = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=messages,  # type: ignore[arg-type]
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=2000,
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        raw_json = response.choices[0].message.content or "{}"
        prompt_tokens = response.usage.prompt_tokens if response.usage else None
        completion_tokens = response.usage.completion_tokens if response.usage else None

        return RawExtraction(
            raw_json=raw_json,
            prompt_version=PROMPT_VERSION,
            model_id=self.model_id,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def structure_text(
        self,
        masked_text: str,
        hints: dict[str, Any] | None = None,
    ) -> RawExtraction:
        """Structure OCR masked text into JSON via Kimi."""
        prompt_text = f"Extract all fields from this document text into the required JSON schema:\n\n{masked_text}"
        if hints:
            prompt_text += f"\n\nContext hints: {hints}"

        messages = [
            {"role": "system", "content": get_extraction_system_prompt()},
            {"role": "user", "content": prompt_text},
        ]

        start_time = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=messages,  # type: ignore[arg-type]
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=2000,
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        raw_json = response.choices[0].message.content or "{}"
        prompt_tokens = response.usage.prompt_tokens if response.usage else None
        completion_tokens = response.usage.completion_tokens if response.usage else None

        return RawExtraction(
            raw_json=raw_json,
            prompt_version=PROMPT_VERSION,
            model_id=self.model_id,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
