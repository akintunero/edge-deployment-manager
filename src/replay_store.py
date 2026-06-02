#!/usr/bin/env python3
"""Durable and in-memory nonce replay protection for signed commands."""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .command_envelope import CommandValidationError


class ReplayStore(ABC):
    """Tracks seen (issuer, nonce) pairs within a TTL window."""

    @abstractmethod
    def check_and_store(
        self,
        issuer: str,
        nonce: str,
        ttl_seconds: int,
        now: Optional[float] = None,
    ) -> None:
        """Reject duplicate nonces; store new nonces until they expire."""


class MemoryReplayStore(ReplayStore):
    """In-process replay store (non-durable across restarts)."""

    def __init__(self) -> None:
        self._entries: Dict[Tuple[str, str], float] = {}
        self._lock = threading.Lock()

    def check_and_store(
        self,
        issuer: str,
        nonce: str,
        ttl_seconds: int,
        now: Optional[float] = None,
    ) -> None:
        current = now if now is not None else time.time()
        key = (issuer, nonce)
        with self._lock:
            self._purge(current)
            if key in self._entries:
                raise CommandValidationError("replay detected: nonce already used")
            self._entries[key] = current + ttl_seconds

    def _purge(self, now: float) -> None:
        expired = [entry for entry, expiry in self._entries.items() if expiry <= now]
        for entry in expired:
            del self._entries[entry]


class SqliteReplayStore(ReplayStore):
    """File-backed replay store surviving agent restarts."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path, timeout=30.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS command_nonces (
                    issuer TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    PRIMARY KEY (issuer, nonce)
                )
                """)
            connection.execute(
                ("CREATE INDEX IF NOT EXISTS idx_command_nonces_expires " "ON command_nonces (expires_at)")
            )
            connection.commit()

    def check_and_store(
        self,
        issuer: str,
        nonce: str,
        ttl_seconds: int,
        now: Optional[float] = None,
    ) -> None:
        current = now if now is not None else time.time()
        expires_at = current + ttl_seconds

        with self._lock:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "DELETE FROM command_nonces WHERE expires_at <= ?",
                    (current,),
                )
                row = connection.execute(
                    "SELECT 1 FROM command_nonces WHERE issuer = ? AND nonce = ?",
                    (issuer, nonce),
                ).fetchone()
                if row is not None:
                    connection.execute("ROLLBACK")
                    raise CommandValidationError("replay detected: nonce already used")

                connection.execute(
                    "INSERT INTO command_nonces (issuer, nonce, expires_at) VALUES (?, ?, ?)",
                    (issuer, nonce, expires_at),
                )
                connection.commit()


class RedisReplayStore(ReplayStore):
    """Shared replay store for horizontally scaled edge agents."""

    def __init__(self, url: str, key_prefix: str = "edge:nonce") -> None:
        try:
            import redis
        except ImportError as exc:
            raise ValueError(
                "redis package is required for replay_store.type=redis; " "pip install 'edge-deployment-manager[redis]'"
            ) from exc

        self._client = redis.from_url(url, decode_responses=True)
        self._prefix = key_prefix.rstrip(":")

    def check_and_store(
        self,
        issuer: str,
        nonce: str,
        ttl_seconds: int,
        now: Optional[float] = None,
    ) -> None:
        del now
        key = f"{self._prefix}:{issuer}:{nonce}"
        stored = self._client.set(key, "1", nx=True, ex=max(ttl_seconds, 1))
        if not stored:
            raise CommandValidationError("replay detected: nonce already used")


def build_replay_store(config: Dict[str, Any]) -> ReplayStore:
    """Create a replay store from security.replay_store settings."""
    store_type = str(config.get("type", "sqlite")).strip().lower()
    if store_type == "memory":
        return MemoryReplayStore()

    if store_type == "redis":
        url = config.get("url") or os.environ.get(str(config.get("url_env", "EDGE_REDIS_URL")), "")
        if not url:
            raise ValueError("replay_store redis requires url or EDGE_REDIS_URL")
        return RedisReplayStore(str(url), key_prefix=str(config.get("key_prefix", "edge:nonce")))

    if store_type == "sqlite":
        path = Path(config.get("path", "data/replay-nonces.db"))
        return SqliteReplayStore(path)

    raise ValueError(f"unsupported replay_store.type: {store_type}")
