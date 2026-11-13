from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    KIMI_API_KEY: str = ""
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "moonshot-v1-8k-vision-preview"
    LLM_MODE: Literal["live", "replay"] = "replay"
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    DATABASE_URL: str = "sqlite:///./ledgersense.db"

    @model_validator(mode="after")
    def validate_live_mode_requirements(self) -> Settings:
        if self.LLM_MODE == "live":
            if not self.KIMI_API_KEY or not self.KIMI_API_KEY.strip():
                raise ValueError("KIMI_API_KEY is required when LLM_MODE is 'live'")
            if not self.KIMI_BASE_URL or not self.KIMI_BASE_URL.strip():
                raise ValueError("KIMI_BASE_URL is required when LLM_MODE is 'live'")
            if not self.KIMI_MODEL or not self.KIMI_MODEL.strip():
                raise ValueError("KIMI_MODEL is required when LLM_MODE is 'live'")
        return self

    @property
    def root_dir(self) -> Path:
        # Resolves to repo root
        return Path(__file__).resolve().parents[4]

    @property
    def data_dir(self) -> Path:
        return self.root_dir / "data"

    @property
    def golden_dir(self) -> Path:
        return self.data_dir / "golden"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"


settings = Settings()
