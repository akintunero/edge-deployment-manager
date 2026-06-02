#!/usr/bin/env python3
"""Bootstrap hardening tests (token hash, rate limits)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
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
from src.rate_limit import RateLimiter


class TestBootstrapHardening(unittest.TestCase):
    """Bootstrap token hash and rate limit tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.registry_path = Path(self.temp_dir) / "devices.json"
        self.audit_path = Path(self.temp_dir) / "audit.log"
        self.ca_cert = Path(self.temp_dir) / "ca.crt"
        self.ca_key = Path(self.temp_dir) / "ca.key"
        DeviceCertificateAuthority.generate_ca(self.ca_cert, self.ca_key)

        signing_key = ed25519.Ed25519PrivateKey.generate()
        os.environ["CONTROL_PLANE_API_TOKEN"] = "api-token"
        os.environ.pop("EDGE_BOOTSTRAP_TOKEN", None)
        os.environ["EDGE_BOOTSTRAP_TOKEN_HASH"] = hashlib.sha256(
            b"bootstrap-token"
        ).hexdigest()
        os.environ["EDGE_COMMAND_SIGNING_KEY_HEX"] = (
            signing_key.private_bytes_raw().hex()
        )

        secrets = SecretProvider(secrets_dir=Path(self.temp_dir) / "no-secrets")
        registry = DeviceRegistry(self.registry_path)
        audit = AuditLog(self.audit_path)
        ca = DeviceCertificateAuthority(self.ca_cert, self.ca_key)
        bootstrap = BootstrapService(
            {
                "token_hash_env": "EDGE_BOOTSTRAP_TOKEN_HASH",
                "default_policy": {"allowed_actions": ["deploy"]},
                "credential_paths": {},
                "agent_config_template": {"mqtt": {"broker": "localhost"}},
            },
            registry,
            audit,
            ca,
            secrets,
        )

        service = ControlPlaneService(
            registry=registry,
            mqtt_publisher=MqttCommandPublisher({"broker": "localhost"}),
            audit_log=audit,
            signing_config={"issuer": "control-plane"},
            secret_provider=secrets,
        )

        self.httpd = ControlPlaneHttpServer(
            ("127.0.0.1", 0),
            registry=registry,
            service=service,
            audit=audit,
            api_token="api-token",
            bootstrap_service=bootstrap,
            bootstrap_rate_limiter=RateLimiter(max_requests=1, window_seconds=60),
        )
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.thread.join(timeout=2)
        shutil.rmtree(self.temp_dir)
        os.environ.pop("CONTROL_PLANE_API_TOKEN", None)
        os.environ.pop("EDGE_BOOTSTRAP_TOKEN_HASH", None)
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

    def _enroll(self, device_id: str, token: str = "bootstrap-token") -> int:
        payload = json.dumps(
            {"device_id": device_id, "csr_pem": self._build_csr(device_id)}
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/bootstrap/enroll",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Bootstrap-Token": token,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code

    def test_token_hash_accepts_valid_token(self) -> None:
        self.assertEqual(self._enroll("edge-agent-hash-001"), 201)

    def test_rate_limit_blocks_burst_enrollment(self) -> None:
        self.assertEqual(self._enroll("edge-agent-rate-001"), 201)
        self.assertEqual(self._enroll("edge-agent-rate-002"), 429)


if __name__ == "__main__":
    unittest.main()
