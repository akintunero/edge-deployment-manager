#!/usr/bin/env python3
"""Tests for internal PKI certificate issuance."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from src.pki.ca import DeviceCertificateAuthority, PkiError


class TestDeviceCertificateAuthority(unittest.TestCase):
    """PKI issuance tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.ca_cert = Path(self.temp_dir) / "ca.crt"
        self.ca_key = Path(self.temp_dir) / "ca.key"
        DeviceCertificateAuthority.generate_ca(self.ca_cert, self.ca_key)
        self.ca = DeviceCertificateAuthority(self.ca_cert, self.ca_key)

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

    def test_issue_client_certificate(self) -> None:
        cert_pem, ca_pem = self.ca.issue_client_certificate(
            csr_pem=self._build_csr("edge-agent-001"),
            device_id="edge-agent-001",
        )
        self.assertIn("BEGIN CERTIFICATE", cert_pem)
        self.assertIn("BEGIN CERTIFICATE", ca_pem)

    def test_reject_mismatched_common_name(self) -> None:
        with self.assertRaises(PkiError):
            self.ca.issue_client_certificate(
                csr_pem=self._build_csr("other-name"),
                device_id="edge-agent-001",
            )


if __name__ == "__main__":
    unittest.main()
