#!/usr/bin/env python3
"""Persistent device registry for the control plane."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class RegistryError(ValueError):
    """Raised when registry operations fail."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class DeviceRegistry:
    """File-backed registry of edge devices and policies."""

    def __init__(self, registry_path: Path) -> None:
        self._path = registry_path
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write({"devices": {}})

    def list_devices(self) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            return [deepcopy(device) for device in data["devices"].values()]

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            device = self._read()["devices"].get(device_id)
            return deepcopy(device) if device else None

    def register_device(self, device_id: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            if device_id in data["devices"]:
                raise RegistryError(f"device already exists: {device_id}")

            now = _utc_now()
            record = {
                "device_id": device_id,
                "status": "active",
                "policy": deepcopy(policy),
                "created_at": now,
                "updated_at": now,
            }
            data["devices"][device_id] = record
            self._write(data)
            return deepcopy(record)

    def update_policy(self, device_id: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            device = data["devices"].get(device_id)
            if device is None:
                raise RegistryError(f"device not found: {device_id}")

            device["policy"] = deepcopy(policy)
            device["updated_at"] = _utc_now()
            self._write(data)
            return deepcopy(device)

    def _read(self) -> Dict[str, Any]:
        with self._path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise RegistryError("registry file must contain a JSON object")
        return data

    def _write(self, data: Dict[str, Any]) -> None:
        temp_path = self._path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        temp_path.replace(self._path)
