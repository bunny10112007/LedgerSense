#!/usr/bin/env python3
"""Reset LedgerSense database and uploads folder for a fresh demo run."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Add backend/src to sys.path so ledgersense package is importable
repo_root = Path(__file__).resolve().parents[1]
backend_src = repo_root / "backend" / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from ledgersense.db.session import init_db


def reset_demo() -> None:
    print("[*] Resetting LedgerSense demo environment...")

    # 1. Remove SQLite database files
    db_candidates = [
        repo_root / "backend" / "ledgersense.db",
        repo_root / "ledgersense.db",
    ]
    for db_path in db_candidates:
        if db_path.exists():
            print(f"[-] Deleting database file: {db_path.name}")
            try:
                db_path.unlink()
            except OSError as err:
                print(f"[!] Warning: Could not delete {db_path}: {err}")

    # 2. Clear uploads directory while preserving .gitkeep
    uploads_dir = repo_root / "data" / "uploads"
    if uploads_dir.exists():
        for item in uploads_dir.iterdir():
            if item.name == ".gitkeep":
                continue
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                try:
                    item.unlink()
                except OSError:
                    pass
    uploads_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = uploads_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    print("[+] data/uploads/ cleaned.")

    # 3. Re-initialize database schema and SQLite triggers
    init_db()
    print(
        "[+] Database tables and append-only audit triggers re-initialized successfully."
    )
    print("[OK] Demo reset complete.")


if __name__ == "__main__":
    reset_demo()
