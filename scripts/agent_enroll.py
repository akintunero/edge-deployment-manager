#!/usr/bin/env python3
"""Enroll an edge agent via the control plane bootstrap API."""

from __future__ import annotations

import argparse
import json
import ssl
import urllib.request
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate_csr(device_id: str, key_path: Path) -> str:
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
        .subject_name(
            x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, device_id),
                ]
            )
        )
        .sign(private_key, hashes.SHA256())
    )
    return csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap enroll an edge agent")
    parser.add_argument("--control-plane-url", required=True, help="https://host:port")
    parser.add_argument("--device-id", required=True, help="Edge device identifier")
    parser.add_argument("--bootstrap-token", required=True, help="Bootstrap token")
    parser.add_argument("--credential-dir", default="/etc/edge", help="Credential output dir")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS verification (dev only)")
    args = parser.parse_args()

    credential_dir = Path(args.credential_dir)
    key_path = credential_dir / "agent.key"
    csr_pem = generate_csr(args.device_id, key_path)

    payload = json.dumps({"device_id": args.device_id, "csr_pem": csr_pem}).encode("utf-8")
    request = urllib.request.Request(
        f"{args.control_plane_url.rstrip('/')}/v1/bootstrap/enroll",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Bootstrap-Token": args.bootstrap_token,
        },
        method="POST",
    )

    context = None
    if args.control_plane_url.startswith("https://"):
        context = ssl.create_default_context()
        if args.insecure:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(request, context=context) as response:
        result = json.loads(response.read().decode("utf-8"))

    credential_dir.mkdir(parents=True, exist_ok=True)
    ca_path = credential_dir / "ca.crt"
    cert_path = credential_dir / "agent.crt"
    ca_path.write_text(result["ca_chain_pem"], encoding="utf-8")
    cert_path.write_text(result["certificate_pem"], encoding="utf-8")

    config_path = credential_dir / "agent-config.json"
    config_path.write_text(json.dumps(result["agent_config"], indent=2), encoding="utf-8")

    print(f"Enrollment complete for {args.device_id}")
    print(f"Wrote CA: {ca_path}")
    print(f"Wrote certificate: {cert_path}")
    print(f"Private key: {key_path}")
    print(f"Suggested agent config: {config_path}")


if __name__ == "__main__":
    main()
