from __future__ import annotations

import pytest
from pydantic import ValidationError

from ledgersense.core.config import Settings


def test_settings_default_values():
    s = Settings(
        ARGON_API_KEY="",
        ARGON_BASE_URL="https://api.argon.ai/v1",
        ARGON_MODEL="argon-vision-v1",
        LLM_MODE="replay",
    )
    assert s.ARGON_MODEL == "argon-vision-v1"
    assert s.ARGON_BASE_URL == "https://api.argon.ai/v1"
    assert s.KIMI_MODEL == "argon-vision-v1"
    assert s.KIMI_BASE_URL == "https://api.argon.ai/v1"
    assert s.KIMI_API_KEY == ""


def test_settings_backward_compat_property_setters():
    s = Settings(LLM_MODE="replay")
    s.KIMI_API_KEY = "test-key"
    s.KIMI_BASE_URL = "https://custom.base.url"
    s.KIMI_MODEL = "custom-model"

    assert s.ARGON_API_KEY == "test-key"
    assert s.ARGON_BASE_URL == "https://custom.base.url"
    assert s.ARGON_MODEL == "custom-model"
    assert s.KIMI_API_KEY == "test-key"
    assert s.KIMI_BASE_URL == "https://custom.base.url"
    assert s.KIMI_MODEL == "custom-model"


def test_settings_live_mode_validation_missing_key():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ARGON_API_KEY="",
            ARGON_BASE_URL="https://api.argon.ai/v1",
            ARGON_MODEL="argon-vision-v1",
            LLM_MODE="live",
        )
    assert "ARGON_API_KEY is required when LLM_MODE is 'live'" in str(exc_info.value)


def test_settings_live_mode_validation_success():
    s = Settings(
        ARGON_API_KEY="sk-live-key",
        ARGON_BASE_URL="https://api.argon.ai/v1",
        ARGON_MODEL="argon-vision-v1",
        LLM_MODE="live",
    )
    assert s.ARGON_API_KEY == "sk-live-key"
    assert s.LLM_MODE == "live"
