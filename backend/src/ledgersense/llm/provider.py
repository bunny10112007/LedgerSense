from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class RawExtraction(BaseModel):
    """Raw extraction response from perception provider."""

    raw_json: str  # exactly what the model returned
    prompt_version: str
    model_id: str
    latency_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@runtime_checkable
class Provider(Protocol):
    """Protocol for perception providers."""

    model_id: str

    def extract_receipt(
        self,
        image_bytes: bytes,
        mime: str = "image/png",
        hints: dict[str, Any] | None = None,
        error_feedback: str | None = None,
    ) -> RawExtraction:
        ...

    def structure_text(
        self,
        masked_text: str,
        hints: dict[str, Any] | None = None,
        error_feedback: str | None = None,
    ) -> RawExtraction:
        ...
