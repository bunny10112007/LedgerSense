from __future__ import annotations

from ledgersense.llm.argon_provider import ArgonProvider

# Backward-compatible alias for KimiProvider
KimiProvider = ArgonProvider

__all__ = ["ArgonProvider", "KimiProvider"]
