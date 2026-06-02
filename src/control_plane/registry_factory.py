#!/usr/bin/env python3
"""Construct a device registry backend from control plane configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..secrets import SecretProvider
from .postgres_registry import PostgresDeviceRegistry
from .registry import DeviceRegistry
from .sqlite_registry import SqliteDeviceRegistry

RegistryBackend = Union[DeviceRegistry, SqliteDeviceRegistry, PostgresDeviceRegistry]


def resolve_database_url(
    config: Dict[str, Any],
    secret_provider: Optional[SecretProvider] = None,
) -> str:
    """Resolve a PostgreSQL connection URL from config and secrets."""
    direct_url = config.get("url")
    if direct_url:
        return str(direct_url).strip()

    env_name = str(config.get("url_env", "CONTROL_PLANE_DATABASE_URL"))
    if secret_provider is not None:
        return secret_provider.get(env_name)

    url = os.environ.get(env_name, "").strip()
    if not url:
        raise ValueError(f"{env_name} must be set for postgres registry")
    return url


def build_device_registry(
    config: Dict[str, Any],
    secret_provider: Optional[SecretProvider] = None,
) -> RegistryBackend:
    """Create a JSON, SQLite, or PostgreSQL registry."""
    backend = str(config.get("backend", "json")).strip().lower()
    if backend == "json":
        path = Path(config.get("path", "data/devices.json"))
        return DeviceRegistry(path)

    if backend == "sqlite":
        path = Path(config.get("path", "data/devices.db"))
        return SqliteDeviceRegistry(path)

    if backend == "postgres":
        database_url = resolve_database_url(config, secret_provider)
        return PostgresDeviceRegistry(database_url)

    raise ValueError(f"unsupported registry.backend: {backend}")
