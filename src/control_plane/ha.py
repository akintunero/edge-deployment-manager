#!/usr/bin/env python3
"""HA control plane wiring helpers."""

from __future__ import annotations

import os
import socket
from typing import Any, Dict, Optional

from ..secrets import SecretProvider
from .leader_election import LeaderElector
from .registry_factory import resolve_database_url


def build_leader_elector(
    config: Dict[str, Any],
    registry_config: Dict[str, Any],
    secret_provider: SecretProvider,
) -> Optional[LeaderElector]:
    """Create a leader elector when HA mode is enabled."""
    ha_cfg = config.get("ha", {})
    if not ha_cfg.get("enabled", False):
        return None

    if str(registry_config.get("backend", "")).strip().lower() != "postgres":
        raise ValueError("ha.enabled requires registry.backend=postgres")

    database_url = resolve_database_url(registry_config, secret_provider)
    holder_env = str(ha_cfg.get("holder_id_env", "HOSTNAME"))
    holder_id = os.environ.get(holder_env, "").strip() or socket.gethostname()
    lock_key = int(ha_cfg.get("leader_lock_key", 84001))
    poll_interval = float(ha_cfg.get("poll_interval_seconds", 2.0))

    elector = LeaderElector(
        database_url=database_url,
        lock_key=lock_key,
        holder_id=holder_id,
        poll_interval_seconds=poll_interval,
    )
    elector.start()
    return elector
