#!/usr/bin/env python3
"""PostgreSQL-backed device registry for HA control plane deployments."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .migrations import apply_migrations
from .registry import RegistryError, _utc_now


class PostgresDeviceRegistry:
    """Shared device registry backed by PostgreSQL."""

    def __init__(self, database_url: str) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise ValueError(
                "psycopg is required for registry.backend=postgres; " "pip install 'edge-deployment-manager[postgres]'"
            ) from exc

        self._database_url = database_url
        self._lock = threading.Lock()
        self._psycopg = psycopg
        self._init_db()

    def list_devices(self) -> List[Dict[str, Any]]:
        with self._lock:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT device_id, status, policy_json, created_at, updated_at "
                        "FROM devices ORDER BY device_id"
                    )
                    rows = cursor.fetchall()
            return [self._row_to_device(row) for row in rows]

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT device_id, status, policy_json, created_at, updated_at "
                        "FROM devices WHERE device_id = %s",
                        (device_id,),
                    )
                    row = cursor.fetchone()
            return self._row_to_device(row) if row else None

    def register_device(self, device_id: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            now_dt = datetime.now(timezone.utc)
            record = {
                "device_id": device_id,
                "status": "active",
                "policy": deepcopy(policy),
                "created_at": _utc_now(),
                "updated_at": _utc_now(),
            }
            try:
                with self._connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO devices (device_id, status, policy_json, created_at, updated_at)
                            VALUES (%s, %s, %s::jsonb, %s, %s)
                            """,
                            (
                                device_id,
                                record["status"],
                                json.dumps(record["policy"], sort_keys=True),
                                now_dt,
                                now_dt,
                            ),
                        )
                    connection.commit()
            except self._psycopg.errors.UniqueViolation as exc:
                raise RegistryError(f"device already exists: {device_id}") from exc
            return deepcopy(record)

    def update_policy(self, device_id: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT device_id FROM devices WHERE device_id = %s",
                        (device_id,),
                    )
                    if cursor.fetchone() is None:
                        raise RegistryError(f"device not found: {device_id}")

                    updated_at = datetime.now(timezone.utc)
                    cursor.execute(
                        """
                        UPDATE devices
                        SET policy_json = %s::jsonb, updated_at = %s
                        WHERE device_id = %s
                        RETURNING device_id, status, policy_json, created_at, updated_at
                        """,
                        (json.dumps(policy, sort_keys=True), updated_at, device_id),
                    )
                    row = cursor.fetchone()
                connection.commit()
            return self._row_to_device(row)

    def _connect(self) -> Any:
        return self._psycopg.connect(self._database_url)

    def _init_db(self) -> None:
        with self._connect() as connection:
            apply_migrations(connection)

    @staticmethod
    def _row_to_device(row: tuple[Any, ...]) -> Dict[str, Any]:
        device_id, status, policy_json, created_at, updated_at = row
        if isinstance(policy_json, dict):
            policy = policy_json
        else:
            policy = json.loads(policy_json)
        if not isinstance(policy, dict):
            raise RegistryError("stored device policy must be a JSON object")

        return {
            "device_id": device_id,
            "status": status,
            "policy": policy,
            "created_at": _format_timestamp(created_at),
            "updated_at": _format_timestamp(updated_at),
        }


def _format_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    return str(value)
