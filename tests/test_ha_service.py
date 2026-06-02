#!/usr/bin/env python3
"""HA command issuance tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.control_plane.audit import AuditLog
from src.control_plane.mqtt_publisher import MqttCommandPublisher
from src.control_plane.registry import DeviceRegistry
from src.control_plane.service import ControlPlaneNotLeaderError, ControlPlaneService


class TestHaControlPlaneService(unittest.TestCase):
    """Leader-gated command publishing tests."""

    def test_follower_rejects_command_publish(self) -> None:
        temp_dir = tempfile.mkdtemp()
        registry = DeviceRegistry(Path(temp_dir) / "devices.json")
        registry.register_device(
            "edge-agent-001",
            {
                "allowed_actions": ["deploy"],
                "allowed_deployment_types": ["docker"],
                "allowed_images": ["nginx:*"],
            },
        )

        signing_key = Ed25519PrivateKey.generate()
        elector = MagicMock()
        elector.is_leader = False

        service = ControlPlaneService(
            registry=registry,
            mqtt_publisher=MqttCommandPublisher({"broker": "localhost"}),
            audit_log=AuditLog(Path(temp_dir) / "audit.log"),
            signing_config={"issuer": "control-plane"},
            secret_provider=MagicMock(
                get=MagicMock(return_value=signing_key.private_bytes_raw().hex())
            ),
            leader_elector=elector,
        )

        with self.assertRaises(ControlPlaneNotLeaderError):
            service.issue_command(
                "edge-agent-001",
                "deploy",
                {"type": "docker", "name": "web", "image": "nginx:latest"},
            )


if __name__ == "__main__":
    unittest.main()
