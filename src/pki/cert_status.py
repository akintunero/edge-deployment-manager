#!/usr/bin/env python3
"""Certificate expiry inspection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cryptography import x509


@dataclass(frozen=True)
class CertificateStatus:
    """Parsed certificate lifetime metadata."""

    not_valid_after: datetime
    days_remaining: int
    needs_rotation: bool


def inspect_certificate_pem(
    certificate_pem: str,
    *,
    rotation_threshold_days: int = 30,
    now: Optional[datetime] = None,
) -> CertificateStatus:
    """Return expiry metadata for a PEM-encoded X.509 certificate."""
    if rotation_threshold_days < 1:
        raise ValueError("rotation_threshold_days must be at least 1")

    cert = x509.load_pem_x509_certificate(certificate_pem.encode("utf-8"))
    not_valid_after = cert.not_valid_after_utc
    current = now or datetime.now(timezone.utc)
    remaining = (not_valid_after - current).days
    return CertificateStatus(
        not_valid_after=not_valid_after,
        days_remaining=remaining,
        needs_rotation=remaining <= rotation_threshold_days,
    )


def inspect_certificate_file(
    cert_path: str,
    *,
    rotation_threshold_days: int = 30,
) -> CertificateStatus:
    """Inspect a certificate file on disk."""
    pem = Path(cert_path).read_text(encoding="utf-8")
    return inspect_certificate_pem(pem, rotation_threshold_days=rotation_threshold_days)
