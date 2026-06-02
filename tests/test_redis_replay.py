#!/usr/bin/env python3
"""Tests for Redis replay store."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.command_envelope import CommandValidationError
from src.replay_store import RedisReplayStore, build_replay_store


class TestRedisReplayStore(unittest.TestCase):
    """Redis replay protection tests."""

    @patch("redis.from_url")
    def test_stores_nonce_with_ttl(self, from_url_mock: MagicMock) -> None:
        client = MagicMock()
        client.set.return_value = True
        from_url_mock.return_value = client

        store = RedisReplayStore("redis://localhost:6379/0")
        store.check_and_store("control-plane", "nonce-abc", 60)

        client.set.assert_called_once_with("edge:nonce:control-plane:nonce-abc", "1", nx=True, ex=60)

    @patch("redis.from_url")
    def test_rejects_duplicate_nonce(self, from_url_mock: MagicMock) -> None:
        client = MagicMock()
        client.set.return_value = False
        from_url_mock.return_value = client

        store = RedisReplayStore("redis://localhost:6379/0")
        with self.assertRaises(CommandValidationError):
            store.check_and_store("control-plane", "nonce-dup", 60)

    def test_build_requires_url(self) -> None:
        with self.assertRaises(ValueError):
            build_replay_store({"type": "redis"})


if __name__ == "__main__":
    unittest.main()
