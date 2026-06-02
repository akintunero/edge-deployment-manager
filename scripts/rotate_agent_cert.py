#!/usr/bin/env python3
"""Rotate an enrolled edge agent mTLS certificate via the control plane API."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def _build_csr(device_id: str) -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, device_id)]))
        .sign(private_key, hashes.SHA256())
    )
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return csr_pem, key_pem


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate edge agent certificate")
    parser.add_argument("--control-plane-url", required=True, help="Control plane base URL")
    parser.add_argument("--device-id", required=True, help="Enrolled device identifier")
    parser.add_argument("--api-token", required=True, help="Control plane API bearer token")
    parser.add_argument("--credential-dir", required=True, help="Directory to write PEM files")
    parser.add_argument("--ca-cert", default="", help="Optional CA certificate output path")
    args = parser.parse_args()

    csr_pem, key_pem = _build_csr(args.device_id)
    url = f"{args.control_plane_url.rstrip('/')}/v1/devices/{args.device_id}/certificates/rotate"
    request = urllib.request.Request(
        url,
        data=json.dumps({"csr_pem": csr_pem}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {args.api_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(request, context=context) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"rotation failed ({exc.code}): {body}", file=sys.stderr)
        sys.exit(1)

    cred_dir = Path(args.credential_dir)
    cred_dir.mkdir(parents=True, exist_ok=True)

    cert_path = cred_dir / "agent.crt"
    key_path = cred_dir / "agent.key"
    cert_path.write_text(result["certificate_pem"], encoding="utf-8")
    key_path.write_text(key_pem, encoding="utf-8")

    ca_path = Path(args.ca_cert) if args.ca_cert else cred_dir / "ca.crt"
    ca_path.write_text(result["ca_chain_pem"], encoding="utf-8")

    print(json.dumps({"device_id": args.device_id, "status": result.get("status"), "cert": str(cert_path)}))


if __name__ == "__main__":
    main()
