#!/usr/bin/env python3
"""Internal CA for issuing edge device client certificates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


class PkiError(ValueError):
    """Raised when PKI operations fail."""


class DeviceCertificateAuthority:
    """Signs device CSRs for MQTT mTLS client authentication."""

    def __init__(self, ca_cert_path: Path, ca_key_path: Path) -> None:
        cert_bytes = ca_cert_path.read_bytes()
        key_bytes = ca_key_path.read_bytes()
        self._ca_cert = x509.load_pem_x509_certificate(cert_bytes)
        ca_key = serialization.load_pem_private_key(key_bytes, password=None)
        if not isinstance(ca_key, RSAPrivateKey):
            raise PkiError("CA private key must be RSA")
        self._ca_key = ca_key

    @staticmethod
    def generate_ca(
        ca_cert_path: Path,
        ca_key_path: Path,
        common_name: str = "Edge Deployment Manager Root CA",
    ) -> None:
        """Create a new root CA certificate and private key."""
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Edge Deployment Manager"),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ]
        )
        now = datetime.now(timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(ca_key, hashes.SHA256())
        )

        ca_cert_path.parent.mkdir(parents=True, exist_ok=True)
        ca_key_path.parent.mkdir(parents=True, exist_ok=True)
        ca_cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        ca_key_path.write_bytes(
            ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    @staticmethod
    def generate_server_certificate(
        ca_cert_path: Path,
        ca_key_path: Path,
        server_cert_path: Path,
        server_key_path: Path,
        common_name: str,
        san_dns_names: Tuple[str, ...] = ("localhost",),
    ) -> None:
        """Issue a server TLS certificate signed by the internal CA."""
        ca = DeviceCertificateAuthority(ca_cert_path, ca_key_path)
        server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Edge Deployment Manager"),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ]
        )
        now = datetime.now(timezone.utc)
        san = x509.SubjectAlternativeName([x509.DNSName(name) for name in san_dns_names])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca._ca_cert.subject)
            .public_key(server_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=825))
            .add_extension(san, critical=False)
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
            .sign(ca._ca_key, hashes.SHA256())
        )

        server_cert_path.parent.mkdir(parents=True, exist_ok=True)
        server_key_path.parent.mkdir(parents=True, exist_ok=True)
        server_cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        server_key_path.write_bytes(
            server_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    @staticmethod
    def generate_client_certificate(
        ca_cert_path: Path,
        ca_key_path: Path,
        client_cert_path: Path,
        client_key_path: Path,
        common_name: str,
    ) -> None:
        """Issue a client authentication certificate for MQTT mTLS."""
        ca = DeviceCertificateAuthority(ca_cert_path, ca_key_path)
        client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Edge Deployment Manager"),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ]
        )
        csr = x509.CertificateSigningRequestBuilder().subject_name(subject).sign(client_key, hashes.SHA256())
        cert_pem, _ = ca.issue_client_certificate(
            csr_pem=csr.public_bytes(serialization.Encoding.PEM).decode("utf-8"),
            device_id=common_name,
        )
        client_cert_path.parent.mkdir(parents=True, exist_ok=True)
        client_key_path.parent.mkdir(parents=True, exist_ok=True)
        client_cert_path.write_text(cert_pem, encoding="utf-8")
        client_key_path.write_bytes(
            client_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    def issue_client_certificate(
        self,
        csr_pem: str,
        device_id: str,
        validity_days: int = 365,
    ) -> Tuple[str, str]:
        """Sign a device CSR and return (certificate_pem, ca_chain_pem)."""
        try:
            csr = x509.load_pem_x509_csr(csr_pem.encode("utf-8"))
        except ValueError as exc:
            raise PkiError("invalid CSR PEM") from exc

        if not csr.is_signature_valid:
            raise PkiError("CSR signature is invalid")

        cn = self._extract_common_name(csr.subject)
        if cn != device_id:
            raise PkiError("CSR common name must match device_id")

        now = datetime.now(timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(csr.subject)
            .issuer_name(self._ca_cert.subject)
            .public_key(csr.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=False,
            )
            .sign(self._ca_key, hashes.SHA256())
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
        ca_pem = self._ca_cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
        return cert_pem, ca_pem

    @staticmethod
    def _extract_common_name(name: x509.Name) -> str:
        attrs = name.get_attributes_for_oid(NameOID.COMMON_NAME)
        if not attrs:
            raise PkiError("CSR subject must include common name (CN)")
        return str(attrs[0].value)
