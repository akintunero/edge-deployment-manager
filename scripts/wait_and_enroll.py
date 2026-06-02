#!/usr/bin/env python3
"""Wait for control plane readiness and enroll the edge agent."""

from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[1]


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _build_csr(device_id: str, key_path: Path) -> str:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, device_id)]))
        .sign(private_key, hashes.SHA256())
    )
    return csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")


def _wait_for_health(url: str, timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    while time.time() < deadline:
        try:
            request = urllib.request.Request(url)
            with urllib.request.urlopen(request, context=context, timeout=5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2)

    raise RuntimeError(f"control plane not ready at {url}")


def main() -> None:
    _load_env(ROOT / ".env")

    device_id = os.environ.get("EDGE_AGENT_ID", "edge-agent-001")
    bootstrap_token = os.environ.get("EDGE_BOOTSTRAP_TOKEN", "")
    if not bootstrap_token:
        raise RuntimeError("EDGE_BOOTSTRAP_TOKEN is not set; run make setup-dev first")

    cred_dir = ROOT / "runtime" / "agent-credentials"
    cred_dir.mkdir(parents=True, exist_ok=True)

    health_url = os.environ.get("CONTROL_PLANE_HEALTH_URL", "https://localhost:8080/health")
    enroll_url = health_url.replace("/health", "/v1/bootstrap/enroll")

    print(f"Waiting for control plane at {health_url}")
    _wait_for_health(health_url)

    csr_pem = _build_csr(device_id, cred_dir / "agent.key")
    payload = json.dumps({"device_id": device_id, "csr_pem": csr_pem}).encode("utf-8")
    request = urllib.request.Request(
        enroll_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Bootstrap-Token": bootstrap_token,
        },
        method="POST",
    )

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(request, context=context) as response:
        result = json.loads(response.read().decode("utf-8"))

    (cred_dir / "ca.crt").write_text(result["ca_chain_pem"], encoding="utf-8")
    (cred_dir / "agent.crt").write_text(result["certificate_pem"], encoding="utf-8")

    agent_config_path = ROOT / "runtime" / "agent-config.yaml"
    agent_config_path.write_text(
        yaml.safe_dump(result["agent_config"], sort_keys=False),
        encoding="utf-8",
    )

    print(f"Enrolled device {device_id}")
    print(f"Credentials written to {cred_dir}")


if __name__ == "__main__":
    main()
