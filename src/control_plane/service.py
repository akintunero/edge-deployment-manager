#!/usr/bin/env python3
"""Control plane business logic for issuing signed commands."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from ..command_envelope import parse_command_payload
from ..command_security import build_signed_command
from ..deploy_policy import enforce_deploy_policy
from ..observability import METRICS
from ..secrets import SecretProvider
from .audit import AuditLog
from .leader_election import LeaderElector
from .mqtt_publisher import MqttCommandPublisher
from .registry_factory import RegistryBackend


class ControlPlaneError(ValueError):
    """Raised when control plane operations are invalid."""


class ControlPlaneNotLeaderError(ControlPlaneError):
    """Raised when a follower replica receives a command publish request."""


class ControlPlaneService:
    """Coordinates registry, signing, MQTT publish, and audit."""

    def __init__(
        self,
        registry: RegistryBackend,
        mqtt_publisher: MqttCommandPublisher,
        audit_log: AuditLog,
        signing_config: Dict[str, Any],
        secret_provider: Optional[SecretProvider] = None,
        leader_elector: Optional[LeaderElector] = None,
    ) -> None:
        self._registry = registry
        self._mqtt = mqtt_publisher
        self._audit = audit_log
        self._issuer = signing_config.get("issuer", "control-plane")
        self._private_key_hex = self._load_private_key(signing_config, secret_provider)
        self._leader_elector = leader_elector

    def issue_command(self, device_id: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if self._leader_elector is not None and not self._leader_elector.is_leader:
            raise ControlPlaneNotLeaderError("this replica is not the active leader")

        device = self._registry.get_device(device_id)
        if device is None:
            raise ControlPlaneError(f"device not found: {device_id}")

        if device.get("status") != "active":
            raise ControlPlaneError(f"device is not active: {device_id}")

        policy = device.get("policy", {})
        allowed_actions = policy.get("allowed_actions", ["deploy"])
        if action not in allowed_actions:
            raise ControlPlaneError(f"action not allowed by device policy: {action}")

        if action == "deploy":
            enforce_deploy_policy(params, policy)

        signed = build_signed_command(
            device_id=device_id,
            issuer=self._issuer,
            action=action,
            params=params,
            private_key_hex=self._private_key_hex,
        )

        # Validate envelope shape before publishing.
        parse_command_payload(json.dumps(signed))

        payload = json.dumps(signed)
        self._mqtt.publish_command(payload)
        METRICS.inc("control_plane_commands_published_total")

        self._audit.record(
            "command_issued",
            {
                "device_id": device_id,
                "command_id": signed["command_id"],
                "action": action,
                "issuer": self._issuer,
                "topic": self._mqtt.command_topic,
            },
        )

        return {
            "command_id": signed["command_id"],
            "device_id": device_id,
            "action": action,
            "topic": self._mqtt.command_topic,
            "status": "published",
        }

    def _load_private_key(
        self,
        signing_config: Dict[str, Any],
        secret_provider: Optional[SecretProvider],
    ) -> str:
        env_name = str(signing_config.get("private_key_env", "EDGE_COMMAND_SIGNING_KEY_HEX"))
        if secret_provider is None:
            raise ControlPlaneError("secret provider is required for signing key resolution")
        return secret_provider.get(env_name)
