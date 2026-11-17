from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ARGON_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("ARGON_API_KEY", "KIMI_API_KEY"),
    )
    ARGON_BASE_URL: str = Field(
        default="https://api.argon.ai/v1",
        validation_alias=AliasChoices("ARGON_BASE_URL", "KIMI_BASE_URL"),
    )
    ARGON_MODEL: str = Field(
        default="argon-vision-v1",
        validation_alias=AliasChoices("ARGON_MODEL", "KIMI_MODEL"),
    )
    LLM_MODE: Literal["live", "replay"] = "replay"
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    DATABASE_URL: str = "sqlite:///./ledgersense.db"

    @model_validator(mode="after")
    def validate_live_mode_requirements(self) -> Settings:
        if self.LLM_MODE == "live":
            if not self.ARGON_API_KEY or not self.ARGON_API_KEY.strip():
                raise ValueError("ARGON_API_KEY is required when LLM_MODE is 'live'")
            if not self.ARGON_BASE_URL or not self.ARGON_BASE_URL.strip():
                raise ValueError("ARGON_BASE_URL is required when LLM_MODE is 'live'")
            if not self.ARGON_MODEL or not self.ARGON_MODEL.strip():
                raise ValueError("ARGON_MODEL is required when LLM_MODE is 'live'")
        return self

    @property
    def KIMI_API_KEY(self) -> str:
        return self.ARGON_API_KEY

    @KIMI_API_KEY.setter
    def KIMI_API_KEY(self, value: str) -> None:
        self.ARGON_API_KEY = value

    @property
    def KIMI_BASE_URL(self) -> str:
        return self.ARGON_BASE_URL

    @KIMI_BASE_URL.setter
    def KIMI_BASE_URL(self, value: str) -> None:
        self.ARGON_BASE_URL = value

    @property
    def KIMI_MODEL(self) -> str:
        return self.ARGON_MODEL

    @KIMI_MODEL.setter
    def KIMI_MODEL(self, value: str) -> None:
        self.ARGON_MODEL = value

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
