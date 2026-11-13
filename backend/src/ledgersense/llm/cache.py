from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from ledgersense.core.config import settings
from ledgersense.db.models import ExtractionCacheRecord
from ledgersense.db.session import engine
from ledgersense.llm.provider import RawExtraction

logger = logging.getLogger(__name__)


class CacheMissError(Exception):
    """Raised when an extraction cache miss occurs in replay mode."""


class ExtractionCache:
    """Extraction cache backed by SQLModel extraction_cache table and filesystem fixtures."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or (settings.golden_dir / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_hash(file_bytes: bytes) -> str:
        """Compute SHA-256 hash of document bytes."""
        return hashlib.sha256(file_bytes).hexdigest()

    def get(
        self,
        file_bytes: bytes,
        model_id: str,
        prompt_version: str,
        session: Session | None = None,
    ) -> RawExtraction | None:
        """Look up cached extraction result.

        In replay mode, raises CacheMissError if no entry is found.
        """
        file_hash = self.compute_hash(file_bytes)

        # 1. Check database table extraction_cache
        cached_json = self._lookup_db(file_hash, model_id, prompt_version, session)

        # 2. Check JSON fixture fallback on disk (data/golden/cache/{file_hash}.json or cache.json)
        if not cached_json:
            cached_json = self._lookup_disk(file_hash, model_id, prompt_version)

        # 3. Handle cache hit
        if cached_json:
            return RawExtraction(
                raw_json=cached_json,
                prompt_version=prompt_version,
                model_id=model_id,
                latency_ms=0,
                prompt_tokens=128,
                completion_tokens=64,
            )

        # 4. Handle cache miss
        if settings.LLM_MODE == "replay":
            raise CacheMissError(
                f"Cache miss in replay mode for file hash: {file_hash} (model: {model_id}, prompt: {prompt_version})"
            )

        return None

    def put(
        self,
        file_bytes: bytes,
        model_id: str,
        prompt_version: str,
        raw_extraction: RawExtraction,
        session: Session | None = None,
    ) -> None:
        """Store extraction result in database and disk cache."""
        file_hash = self.compute_hash(file_bytes)

        # Save to DB
        record = ExtractionCacheRecord(
            file_hash=file_hash,
            model_id=model_id,
            prompt_version=prompt_version,
            response_json=raw_extraction.raw_json,
        )
        if session:
            session.merge(record)
            session.commit()
        else:
            with Session(engine) as s:
                s.merge(record)
                s.commit()

        # Save to disk fixture
        fixture_path = self.cache_dir / f"{file_hash}.json"
        with open(fixture_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "file_hash": file_hash,
                    "model_id": model_id,
                    "prompt_version": prompt_version,
                    "response_json": raw_extraction.raw_json,
                },
                f,
                indent=2,
            )

    def _lookup_db(
        self,
        file_hash: str,
        model_id: str,
        prompt_version: str,
        session: Session | None = None,
    ) -> str | None:
        if session:
            record = session.get(ExtractionCacheRecord, (file_hash, model_id, prompt_version))
            return record.response_json if record else None
        try:
            with Session(engine) as s:
                record = s.get(ExtractionCacheRecord, (file_hash, model_id, prompt_version))
                return record.response_json if record else None
        except (SQLAlchemyError, OSError) as exc:
            logger.debug("Database cache lookup error: %s", exc)
            return None

    def _lookup_disk(
        self,
        file_hash: str,
        model_id: str,
        prompt_version: str,
    ) -> str | None:
        fixture_file = self.cache_dir / f"{file_hash}.json"
        if fixture_file.exists():
            try:
                with open(fixture_file, encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("response_json")
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Disk cache file lookup error: %s", exc)

        # Check multi-cache index file if present
        cache_index = self.cache_dir / "index.json"
        if cache_index.exists():
            try:
                with open(cache_index, encoding="utf-8") as f:
                    index_data = json.load(f)
                key = f"{file_hash}:{model_id}:{prompt_version}"
                return index_data.get(key)
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Disk cache index lookup error: %s", exc)

        return None
