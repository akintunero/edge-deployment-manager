#!/usr/bin/env python3
"""Device onboarding and certificate bootstrap."""

from __future__ import annotations

import hashlib
import secrets
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, cast

from ..pki.ca import DeviceCertificateAuthority, PkiError
from ..pki.cert_status import inspect_certificate_pem
from ..secrets import SecretProvider
from .audit import AuditLog
from .registry_factory import RegistryBackend


class BootstrapError(ValueError):
    """Raised when bootstrap enrollment fails."""


class BootstrapService:
    """One-time device enrollment with mTLS certificate issuance."""

    def __init__(
        self,
        config: Dict[str, Any],
        registry: RegistryBackend,
        audit_log: AuditLog,
        ca: DeviceCertificateAuthority,
        secret_provider: SecretProvider,
    ) -> None:
        self._config = config
        self._registry = registry
        self._audit = audit_log
        self._ca = ca
        self._secret_provider = secret_provider
        self._bootstrap_credential = None
        if config.get("require_bootstrap_token", True):
            self._bootstrap_credential = self._load_bootstrap_credential(config, secret_provider)
        self._default_policy = deepcopy(config.get("default_policy", {}))
        self._validity_days = int(config.get("cert_validity_days", 365))
        self._agent_template = deepcopy(config.get("agent_config_template", {}))

    def enroll(
        self,
        device_id: str,
        csr_pem: str,
        bootstrap_token: str,
    ) -> Dict[str, Any]:
        self._verify_bootstrap_token(bootstrap_token)

        if self._registry.get_device(device_id) is not None:
            raise BootstrapError(f"device already enrolled: {device_id}")

        try:
            certificate_pem, ca_chain_pem = self._ca.issue_client_certificate(
                csr_pem=csr_pem,
                device_id=device_id,
                validity_days=self._validity_days,
            )
        except PkiError as exc:
            raise BootstrapError(str(exc)) from exc

        policy = deepcopy(self._default_policy)
        device = self._registry.register_device(device_id, policy)
        enrolled_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        self._audit.record(
            "device_bootstrapped",
            {
                "device_id": device_id,
                "enrolled_at": enrolled_at,
            },
        )

        credential_paths = deepcopy(self._config.get("credential_paths", {}))
        agent_config = self._build_agent_config(device_id=device_id, credential_paths=credential_paths)

        return {
            "device_id": device_id,
            "status": "enrolled",
            "enrolled_at": enrolled_at,
            "certificate_pem": certificate_pem,
            "ca_chain_pem": ca_chain_pem,
            "credential_paths": credential_paths,
            "device": device,
            "agent_config": agent_config,
        }

    def rotate_certificate(self, device_id: str, csr_pem: str) -> Dict[str, Any]:
        """Issue a new client certificate for an already enrolled device."""
        device = self._registry.get_device(device_id)
        if device is None:
            raise BootstrapError(f"device not enrolled: {device_id}")

        try:
            certificate_pem, ca_chain_pem = self._ca.issue_client_certificate(
                csr_pem=csr_pem,
                device_id=device_id,
                validity_days=self._validity_days,
            )
        except PkiError as exc:
            raise BootstrapError(str(exc)) from exc

        cert_status = inspect_certificate_pem(certificate_pem)
        rotated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        self._audit.record(
            "device_cert_rotated",
            {
                "device_id": device_id,
                "rotated_at": rotated_at,
                "expires_at": cert_status.not_valid_after.isoformat(),
                "days_remaining": cert_status.days_remaining,
            },
        )

        credential_paths = deepcopy(self._config.get("credential_paths", {}))
        return {
            "device_id": device_id,
            "status": "rotated",
            "rotated_at": rotated_at,
            "certificate_pem": certificate_pem,
            "ca_chain_pem": ca_chain_pem,
            "credential_paths": credential_paths,
            "certificate": {
                "not_valid_after": cert_status.not_valid_after.isoformat(),
                "days_remaining": cert_status.days_remaining,
                "needs_rotation": cert_status.needs_rotation,
            },
        }

    def _build_agent_config(
        self,
        device_id: str,
        credential_paths: Dict[str, str],
    ) -> Dict[str, Any]:
        config = deepcopy(self._agent_template)
        security = config.setdefault("security", {})
        security["device_id"] = device_id

        mqtt = config.setdefault("mqtt", {})
        tls = mqtt.setdefault("tls", {})
        tls["enabled"] = True
        if credential_paths.get("ca_cert"):
            tls["ca_cert"] = credential_paths["ca_cert"]
        if credential_paths.get("cert_file"):
            tls["cert_file"] = credential_paths["cert_file"]
        if credential_paths.get("key_file"):
            tls["key_file"] = credential_paths["key_file"]

        return cast(Dict[str, Any], config)

    def _verify_bootstrap_token(self, provided: str) -> None:
        if self._bootstrap_credential is None:
            raise BootstrapError("bootstrap token is not configured")
        kind, expected = self._bootstrap_credential
        if kind == "hash":
            digest = hashlib.sha256(provided.encode("utf-8")).hexdigest()
            if not secrets.compare_digest(digest, expected):
                raise BootstrapError("bootstrap enrollment denied")
            return

        if not secrets.compare_digest(provided, expected):
            raise BootstrapError("bootstrap enrollment denied")

    def _load_bootstrap_credential(
        self,
        config: Dict[str, Any],
        secret_provider: SecretProvider,
    ) -> tuple[str, str]:
        token_hash_env = config.get("token_hash_env")
        if token_hash_env:
            token_hash = secret_provider.get(str(token_hash_env)).lower()
            if len(token_hash) != 64 or not all(ch in "0123456789abcdef" for ch in token_hash):
                raise BootstrapError(f"{token_hash_env} must be a 64-character sha256 hex digest")
            return ("hash", token_hash)

        token_env = str(config.get("token_env", "EDGE_BOOTSTRAP_TOKEN"))
        return ("plain", secret_provider.get(token_env))


def build_bootstrap_service(
    config: Dict[str, Any],
    registry: RegistryBackend,
    audit_log: AuditLog,
    secret_provider: SecretProvider,
) -> BootstrapService:
    """Create bootstrap service when enabled in control plane config."""
    if not config.get("enabled", False):
        raise BootstrapError("bootstrap is not enabled")

    pki_cfg = config.get("pki", {})
    ca_cert = Path(pki_cfg.get("ca_cert", "certs/ca.crt"))
    ca_key = Path(pki_cfg.get("ca_key", "certs/ca.key"))
    ca = DeviceCertificateAuthority(ca_cert, ca_key)
    return BootstrapService(config, registry, audit_log, ca, secret_provider)
