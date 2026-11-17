"""Forwarding wrapper for smoke_argon.py to maintain backward compatibility."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path if needed
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from smoke_argon import main

if __name__ == "__main__":
    main()
