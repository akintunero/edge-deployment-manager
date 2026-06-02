#!/usr/bin/env python3
"""Certificate rotation API tests."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.x509.oid import NameOID

from src.control_plane.api import ControlPlaneHttpServer
from src.control_plane.audit import AuditLog
from src.control_plane.bootstrap import BootstrapService
from src.control_plane.mqtt_publisher import MqttCommandPublisher
from src.control_plane.registry import DeviceRegistry
from src.control_plane.service import ControlPlaneService
from src.pki.ca import DeviceCertificateAuthority
from src.secrets import SecretProvider


class TestCertificateRotation(unittest.TestCase):
    """Rotate certificate endpoint tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.registry_path = Path(self.temp_dir) / "devices.json"
        self.audit_path = Path(self.temp_dir) / "audit.log"
        self.ca_cert = Path(self.temp_dir) / "ca.crt"
        self.ca_key = Path(self.temp_dir) / "ca.key"
        DeviceCertificateAuthority.generate_ca(self.ca_cert, self.ca_key)

        signing_key = ed25519.Ed25519PrivateKey.generate()
        os.environ["CONTROL_PLANE_API_TOKEN"] = "api-token"
        os.environ["EDGE_BOOTSTRAP_TOKEN"] = "bootstrap-token"
        os.environ["EDGE_COMMAND_SIGNING_KEY_HEX"] = signing_key.private_bytes_raw().hex()

        self.secrets = SecretProvider(secrets_dir=Path(self.temp_dir) / "empty-secrets")
        registry = DeviceRegistry(self.registry_path)
        audit = AuditLog(self.audit_path)
        ca = DeviceCertificateAuthority(self.ca_cert, self.ca_key)
        bootstrap = BootstrapService(
            {
                "cert_validity_days": 90,
                "credential_paths": {},
                "require_bootstrap_token": False,
            },
            registry,
            audit,
            ca,
            self.secrets,
        )

        registry.register_device("edge-agent-001", {"allowed_actions": ["deploy"]})

        service = ControlPlaneService(
            registry=registry,
            mqtt_publisher=MqttCommandPublisher({"broker": "localhost"}),
            audit_log=audit,
            signing_config={"issuer": "control-plane"},
            secret_provider=self.secrets,
        )

        self.httpd = ControlPlaneHttpServer(
            ("127.0.0.1", 0),
            registry=registry,
            service=service,
            audit=audit,
            api_token="api-token",
            bootstrap_service=bootstrap,
        )
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.thread.join(timeout=2)
        shutil.rmtree(self.temp_dir)
        os.environ.pop("CONTROL_PLANE_API_TOKEN", None)
        os.environ.pop("EDGE_BOOTSTRAP_TOKEN", None)
        os.environ.pop("EDGE_COMMAND_SIGNING_KEY_HEX", None)

    def _build_csr(self, device_id: str) -> str:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, device_id)])
            )
            .sign(private_key, hashes.SHA256())
        )
        return csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    def test_rotate_certificate_success(self) -> None:
        payload = json.dumps(
            {"csr_pem": self._build_csr("edge-agent-001")}
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/devices/edge-agent-001/certificates/rotate",
            data=payload,
            headers={
                "Authorization": "Bearer api-token",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(result["status"], "rotated")
        self.assertIn("BEGIN CERTIFICATE", result["certificate_pem"])


if __name__ == "__main__":
    unittest.main()
