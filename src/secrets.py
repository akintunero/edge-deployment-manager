#!/usr/bin/env python3
"""Load sensitive values from environment variables and mounted secret files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional


class SecretNotFoundError(RuntimeError):
    """Raised when a required secret cannot be resolved."""


class SecretProvider:
    """
    Resolve secrets for production deployments.

    Resolution order per key:
    1. Environment variable (exact name)
    2. File at secrets_dir/<KEY> (Docker/Kubernetes secret mounts)
    3. File path from <KEY>_FILE environment variable
    """

    def __init__(
        self,
        secrets_dir: Optional[Path] = None,
        *,
        require_non_empty: bool = True,
    ) -> None:
        configured_dir = secrets_dir or Path(os.environ.get("EDGE_SECRETS_DIR", "/run/secrets"))
        self._secrets_dir = configured_dir
        self._require_non_empty = require_non_empty

    @classmethod
    def from_config(cls, config: Optional[Dict[str, Any]]) -> "SecretProvider":
        if not config:
            return cls()
        secrets_dir = config.get("directory")
        path = Path(str(secrets_dir)) if secrets_dir else None
        return cls(
            path,
            require_non_empty=bool(config.get("require_non_empty", True)),
        )

    def get(self, env_name: str) -> str:
        """Return secret value for the given environment variable name."""
        direct = os.environ.get(env_name)
        if direct is not None and (direct.strip() or not self._require_non_empty):
            return direct.strip()

        file_env = os.environ.get(f"{env_name}_FILE", "").strip()
        if file_env:
            return self._read_file(Path(file_env), env_name)

        mounted = self._secrets_dir / env_name
        if mounted.is_file():
            return self._read_file(mounted, env_name)

        raise SecretNotFoundError(f"secret not found for {env_name} " f"(set env, {env_name}_FILE, or mount {mounted})")

    def get_optional(self, env_name: str) -> Optional[str]:
        try:
            value = self.get(env_name)
        except SecretNotFoundError:
            return None
        return value if value else None

    @staticmethod
    def _read_file(path: Path, env_name: str) -> str:
        if not path.is_file():
            raise SecretNotFoundError(f"secret file missing for {env_name}: {path}")
        value = path.read_text(encoding="utf-8").strip()
        if not value:
            raise SecretNotFoundError(f"secret file is empty for {env_name}: {path}")
        return value
