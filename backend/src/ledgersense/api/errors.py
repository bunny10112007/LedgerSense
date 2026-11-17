from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Base API exception following LedgerSense error contract."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(APIError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="NOT_FOUND", message=message, status_code=404, details=details
        )


class GateBlockedError(APIError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="GATE_BLOCKED_HIGH_RISK",
            message=message,
            status_code=409,
            details=details,
        )


class InvalidAuditorDecisionError(APIError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="INVALID_AUDITOR_DECISION",
            message=message,
            status_code=422,
            details=details,
        )


class LLMUnavailableError(APIError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="LLM_UNAVAILABLE",
            message=message,
            status_code=502,
            details=details
            or {"suggestion": "Set LLM_MODE=replay to use cached extractions offline."},
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Unified FastAPI exception handler matching Section 8 error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )
