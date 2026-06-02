#!/usr/bin/env python3
"""Tests for durable command nonce replay protection."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from src.command_envelope import CommandValidationError
from src.replay_store import MemoryReplayStore, SqliteReplayStore


class TestReplayStore(unittest.TestCase):
    """Replay store behavior tests."""

    def test_memory_store_rejects_duplicate_nonce(self) -> None:
        store = MemoryReplayStore()
        store.check_and_store("control-plane", "nonce-a", 60)
        with self.assertRaises(CommandValidationError):
            store.check_and_store("control-plane", "nonce-a", 60)

    def test_sqlite_store_persists_across_instances(self) -> None:
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = Path(temp_dir) / "replay.db"
            first = SqliteReplayStore(db_path)
            first.check_and_store("control-plane", "nonce-b", 60)

            second = SqliteReplayStore(db_path)
            with self.assertRaises(CommandValidationError):
                second.check_and_store("control-plane", "nonce-b", 60)
        finally:
            shutil.rmtree(temp_dir)

    def test_sqlite_store_allows_nonce_after_expiry(self) -> None:
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = Path(temp_dir) / "replay.db"
            store = SqliteReplayStore(db_path)
            store.check_and_store("control-plane", "nonce-c", 1, now=100.0)
            store.check_and_store("control-plane", "nonce-c", 1, now=102.0)
        finally:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
