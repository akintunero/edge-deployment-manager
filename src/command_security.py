#!/usr/bin/env python3
"""Authentication, authorization, replay protection, and signature verification."""

from __future__ import annotations

import base64
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .command_envelope import (
    ENVELOPE_VERSION,
    CommandEnvelope,
    CommandValidationError,
    canonical_signing_bytes,
    parse_command_payload,
)
from .deploy_policy import enforce_deploy_policy
from .replay_store import ReplayStore, build_replay_store

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrustedSigner:
    issuer: str
    public_key: Ed25519PublicKey


class CommandVerifier:
    """Validates signed command envelopes before privileged actions run."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._device_id = config.get("device_id", "").strip()
        if not self._device_id:
            raise ValueError("security.device_id is required")

        self._require_signed = bool(config.get("require_signed_commands", True))
        self._max_clock_skew = int(config.get("max_clock_skew_seconds", 300))
        self._nonce_ttl_seconds = int(config.get("nonce_ttl_seconds", 900))
        self._replay_store = self._build_replay_store(config)
        self._trusted_signers = self._load_trusted_signers(config.get("trusted_signers", []))
        self._policy = config.get("policy", {})

    def verify_payload(self, payload: str) -> CommandEnvelope:
        envelope = parse_command_payload(payload)
        self._verify_device(envelope)
        self._verify_timestamp(envelope)
        self._replay_store.check_and_store(
            envelope.issuer,
            envelope.nonce,
            self._nonce_ttl_seconds,
        )
        self._verify_signature(envelope)
        self._authorize(envelope)
        return envelope

    def _verify_device(self, envelope: CommandEnvelope) -> None:
        if envelope.device_id != self._device_id:
            raise CommandValidationError("command device_id does not match this agent")

    def _verify_timestamp(self, envelope: CommandEnvelope) -> None:
        now = int(time.time())
        delta = abs(now - envelope.timestamp)
        if delta > self._max_clock_skew:
            raise CommandValidationError("command timestamp outside allowed clock skew")

    def _verify_signature(self, envelope: CommandEnvelope) -> None:
        if not self._require_signed and not envelope.signature:
            return

        signer = self._trusted_signers.get(envelope.issuer)
        if signer is None:
            raise CommandValidationError("untrusted command issuer")

        try:
            signature = base64.b64decode(envelope.signature, validate=True)
        except Exception as exc:
            raise CommandValidationError("signature must be base64-encoded") from exc

        message = canonical_signing_bytes(envelope.raw)
        try:
            signer.public_key.verify(signature, message)
        except InvalidSignature as exc:
            raise CommandValidationError("invalid command signature") from exc

    def _authorize(self, envelope: CommandEnvelope) -> None:
        allowed_actions = self._policy.get("allowed_actions", ["deploy"])
        if envelope.action not in allowed_actions:
            raise CommandValidationError(f"action not allowed: {envelope.action}")

        if envelope.action != "deploy":
            return

        deployment_type = envelope.params.get("type", "docker")
        allowed_types = self._policy.get("allowed_deployment_types", ["docker", "kubernetes"])
        if deployment_type not in allowed_types:
            raise CommandValidationError(f"deployment type not allowed: {deployment_type}")

        enforce_deploy_policy(envelope.params, self._policy)

    def _build_replay_store(self, config: Dict[str, Any]) -> ReplayStore:
        replay_cfg = config.get("replay_store")
        if replay_cfg is None:
            return build_replay_store({"type": "sqlite", "path": "data/replay-nonces.db"})
        if not isinstance(replay_cfg, dict):
            raise ValueError("security.replay_store must be an object")
        return build_replay_store(replay_cfg)

    def _load_trusted_signers(self, signers_config: Any) -> Dict[str, TrustedSigner]:
        if not isinstance(signers_config, list) or not signers_config:
            raise ValueError("security.trusted_signers must be a non-empty list")

        trusted: Dict[str, TrustedSigner] = {}
        for entry in signers_config:
            if not isinstance(entry, dict):
                raise ValueError("trusted_signers entries must be objects")

            issuer = str(entry.get("issuer", "")).strip()
            public_key_hex = str(entry.get("public_key_hex", "")).strip()
            if not issuer or not public_key_hex:
                raise ValueError("trusted_signers require issuer and public_key_hex")

            public_key_bytes = bytes.fromhex(public_key_hex)
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            trusted[issuer] = TrustedSigner(issuer=issuer, public_key=public_key)

        return trusted


def build_command_verifier(config: Dict[str, Any]) -> Optional[CommandVerifier]:
    """Create a verifier when security settings are present."""
    security_config = config.get("security")
    if not security_config:
        return None
    return CommandVerifier(security_config)


def sign_command_envelope(
    envelope: Dict[str, Any],
    private_key_hex: str,
) -> Dict[str, Any]:
    """Sign a command envelope (utility for control-plane tooling and tests)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    signing_body = {key: envelope[key] for key in envelope if key != "signature"}
    private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    signature = private_key.sign(canonical_signing_bytes(signing_body))
    signed = dict(envelope)
    signed["signature"] = base64.b64encode(signature).decode("ascii")
    return signed


def load_signing_key_from_env() -> Optional[str]:
    """Load optional control-plane signing key from environment."""
    return os.environ.get("EDGE_COMMAND_SIGNING_KEY_HEX")


def build_signed_command(
    *,
    device_id: str,
    issuer: str,
    action: str,
    params: Dict[str, Any],
    private_key_hex: str,
) -> Dict[str, Any]:
    """Build and sign a command envelope for MQTT delivery."""
    envelope: Dict[str, Any] = {
        "version": ENVELOPE_VERSION,
        "command_id": str(uuid.uuid4()),
        "timestamp": int(time.time()),
        "nonce": secrets.token_urlsafe(16),
        "issuer": issuer,
        "device_id": device_id,
        "action": action,
        "params": params,
        "signature": "",
    }
    return sign_command_envelope(envelope, private_key_hex)
