#!/usr/bin/env python3
"""SQLite-backed device registry for multi-instance control plane deployments."""

from __future__ import annotations

import json
import sqlite3
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .registry import RegistryError, _utc_now


class SqliteDeviceRegistry:
    """SQLite registry of edge devices and policies."""

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def list_devices(self) -> List[Dict[str, Any]]:
        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    (
                        "SELECT device_id, status, policy_json, created_at, updated_at "
                        "FROM devices ORDER BY device_id"
                    ),
                ).fetchall()
            return [self._row_to_device(row) for row in rows]

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    (
                        "SELECT device_id, status, policy_json, created_at, updated_at "
                        "FROM devices WHERE device_id = ?"
                    ),
                    (device_id,),
                ).fetchone()
            return self._row_to_device(row) if row else None

    def register_device(self, device_id: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            now = _utc_now()
            record = {
                "device_id": device_id,
                "status": "active",
                "policy": deepcopy(policy),
                "created_at": now,
                "updated_at": now,
            }
            with self._connect() as connection:
                try:
                    connection.execute(
                        """
                        INSERT INTO devices (device_id, status, policy_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            device_id,
                            record["status"],
                            json.dumps(record["policy"], sort_keys=True),
                            now,
                            now,
                        ),
                    )
                    connection.commit()
                except sqlite3.IntegrityError as exc:
                    raise RegistryError(f"device already exists: {device_id}") from exc
            return deepcopy(record)

    def update_policy(self, device_id: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT device_id FROM devices WHERE device_id = ?",
                    (device_id,),
                ).fetchone()
                if row is None:
                    raise RegistryError(f"device not found: {device_id}")

                updated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                connection.execute(
                    "UPDATE devices SET policy_json = ?, updated_at = ? WHERE device_id = ?",
                    (json.dumps(policy, sort_keys=True), updated_at, device_id),
                )
                connection.commit()

                updated = connection.execute(
                    (
                        "SELECT device_id, status, policy_json, created_at, updated_at "
                        "FROM devices WHERE device_id = ?"
                    ),
                    (device_id,),
                ).fetchone()
            return self._row_to_device(updated)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    policy_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)
            connection.commit()

    @staticmethod
    def _row_to_device(row: sqlite3.Row) -> Dict[str, Any]:
        policy = json.loads(row["policy_json"])
        if not isinstance(policy, dict):
            raise RegistryError("stored device policy must be a JSON object")
        return {
            "device_id": row["device_id"],
            "status": row["status"],
            "policy": policy,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
