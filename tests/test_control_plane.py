#!/usr/bin/env python3
"""Tests for control plane registry and HTTP API."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.control_plane.api import ControlPlaneHttpServer
from src.control_plane.audit import AuditLog
from src.control_plane.mqtt_publisher import MqttCommandPublisher
from src.control_plane.registry import DeviceRegistry
from src.control_plane.service import ControlPlaneService
from src.secrets import SecretProvider


class TestControlPlane(unittest.TestCase):
    """Control plane API integration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = Ed25519PrivateKey.generate()
        cls.public_key_hex = cls.private_key.public_key().public_bytes_raw().hex()
        cls.private_key_hex = cls.private_key.private_bytes_raw().hex()

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.registry_path = Path(self.temp_dir) / "devices.json"
        self.audit_path = Path(self.temp_dir) / "audit.log"

        os.environ["CONTROL_PLANE_API_TOKEN"] = "test-token"
        os.environ["EDGE_COMMAND_SIGNING_KEY_HEX"] = self.private_key_hex

        secrets = SecretProvider(secrets_dir=Path(self.temp_dir) / "no-secrets")
        registry = DeviceRegistry(self.registry_path)
        audit = AuditLog(self.audit_path)
        mqtt = MqttCommandPublisher({"broker": "localhost", "port": 1883})
        service = ControlPlaneService(
            registry=registry,
            mqtt_publisher=mqtt,
            audit_log=audit,
            signing_config={"issuer": "control-plane"},
            secret_provider=secrets,
        )

        self.httpd = ControlPlaneHttpServer(
            ("127.0.0.1", 0),
            registry=registry,
            service=service,
            audit=audit,
            api_token="test-token",
        )
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.thread.join(timeout=2)
        shutil.rmtree(self.temp_dir)
        os.environ.pop("CONTROL_PLANE_API_TOKEN", None)
        os.environ.pop("EDGE_COMMAND_SIGNING_KEY_HEX", None)

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        token: str = "test-token",
    ) -> Tuple[int, Dict[str, Any]]:
        data = None
        headers = {"Authorization": f"Bearer {token}"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload

    def test_health_is_public(self) -> None:
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}/health")
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 200)

    def test_register_list_and_get_device(self) -> None:
        policy = {
            "allowed_actions": ["deploy"],
            "allowed_deployment_types": ["docker"],
            "allowed_images": ["nginx:*"],
        }
        status, created = self._request(
            "POST",
            "/v1/devices",
            {"device_id": "edge-agent-001", "policy": policy},
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["device_id"], "edge-agent-001")

        status, listing = self._request("GET", "/v1/devices")
        self.assertEqual(status, 200)
        self.assertEqual(len(listing["devices"]), 1)

        status, device = self._request("GET", "/v1/devices/edge-agent-001")
        self.assertEqual(status, 200)
        self.assertEqual(device["policy"]["allowed_images"], ["nginx:*"])

    @patch("src.control_plane.mqtt_publisher.MqttCommandPublisher.publish_command")
    def test_issue_signed_command(self, publish_mock) -> None:
        policy = {
            "allowed_actions": ["deploy"],
            "allowed_deployment_types": ["docker"],
            "allowed_images": ["nginx:*"],
        }
        self._request(
            "POST",
            "/v1/devices",
            {"device_id": "edge-agent-001", "policy": policy},
        )

        status, result = self._request(
            "POST",
            "/v1/devices/edge-agent-001/commands",
            {
                "action": "deploy",
                "params": {
                    "type": "docker",
                    "name": "web",
                    "image": "nginx:latest",
                },
            },
        )
        self.assertEqual(status, 202)
        self.assertEqual(result["status"], "published")
        publish_mock.assert_called_once()

        published_payload = publish_mock.call_args[0][0]
        envelope = json.loads(published_payload)
        self.assertEqual(envelope["device_id"], "edge-agent-001")
        self.assertEqual(envelope["issuer"], "control-plane")
        self.assertTrue(envelope["signature"])


if __name__ == "__main__":
    unittest.main()
