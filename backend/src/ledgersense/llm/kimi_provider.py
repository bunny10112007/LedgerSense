from __future__ import annotations

import base64
import random
import threading
import time
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from ledgersense.core.config import settings
from ledgersense.llm.prompts import PROMPT_VERSION, get_extraction_system_prompt
from ledgersense.llm.provider import RawExtraction

# Module-level concurrency limit: at most 4 requests in flight across threads
_DEFAULT_SEMAPHORE = threading.Semaphore(4)


class KimiProvider:
    """Vision and text perception provider using Kimi (Moonshot) via OpenAI-compatible SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_id: str | None = None,
        timeout: float = 60.0,
        client: OpenAI | None = None,
        semaphore: threading.Semaphore | None = None,
    ) -> None:
        self.model_id = model_id or settings.KIMI_MODEL
        self.base_url = base_url or settings.KIMI_BASE_URL
        self.api_key = api_key or settings.KIMI_API_KEY
        self.timeout = timeout
        self.semaphore = semaphore or _DEFAULT_SEMAPHORE

        if client is not None:
            self.client = client
        else:
            api_key_to_use = self.api_key if (self.api_key and self.api_key.strip()) else "replay-mode-key"
            self.client = OpenAI(
                api_key=api_key_to_use,
                base_url=self.base_url,
                timeout=self.timeout,
            )

    def _call_chat_completion(
        self,
        messages: list[dict[str, Any]],
        max_retries: int = 3,
        base_delay: float = 0.5,
    ) -> Any:
        """Execute chat completion with concurrency semaphore and exponential backoff + jitter on 429/5xx."""
        for attempt in range(max_retries):
            try:
                with self.semaphore:
                    return self.client.chat.completions.create(
                        model=self.model_id,
                        messages=messages,  # type: ignore[arg-type]
                        response_format={"type": "json_object"},
                        temperature=0.0,
                        max_tokens=2000,
                    )
            except (RateLimitError, InternalServerError, APIConnectionError):
                if attempt == max_retries - 1:
                    raise
                jitter = random.uniform(0.05, 0.25)
                delay = (base_delay * (2**attempt)) + jitter
                time.sleep(delay)
            except APIStatusError as exc:
                if exc.status_code == 429 or exc.status_code >= 500:
                    if attempt == max_retries - 1:
                        raise
                    jitter = random.uniform(0.05, 0.25)
                    delay = (base_delay * (2**attempt)) + jitter
                    time.sleep(delay)
                else:
                    raise

    def extract_receipt(
        self,
        image_bytes: bytes,
        mime: str = "image/png",
        hints: dict[str, Any] | None = None,
        error_feedback: str | None = None,
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
        if error_feedback:
            user_content.append(
                {
                    "type": "text",
                    "text": (
                        "PREVIOUS ATTEMPT FAILED VALIDATION:\n"
                        f"{error_feedback}\n"
                        "Please correct all errors and return valid JSON conforming to the schema."
                    ),
                }
            )

        messages = [
            {"role": "system", "content": get_extraction_system_prompt()},
            {"role": "user", "content": user_content},
        ]

        start_time = time.perf_counter()
        response = self._call_chat_completion(messages)
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
        error_feedback: str | None = None,
    ) -> RawExtraction:
        """Structure OCR masked text into JSON via Kimi."""
        prompt_text = f"Extract all fields from this document text into the required JSON schema:\n\n{masked_text}"
        if hints:
            prompt_text += f"\n\nContext hints: {hints}"
        if error_feedback:
            prompt_text += (
                "\n\nPREVIOUS ATTEMPT FAILED VALIDATION:\n"
                f"{error_feedback}\n"
                "Please correct all errors and return valid JSON conforming to the schema."
            )

        messages = [
            {"role": "system", "content": get_extraction_system_prompt()},
            {"role": "user", "content": prompt_text},
        ]

        start_time = time.perf_counter()
        response = self._call_chat_completion(messages)
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
