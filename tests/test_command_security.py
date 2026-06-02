#!/usr/bin/env python3
"""Tests for signed command envelope validation and verification."""

import json
import time
import unittest
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.command_envelope import CommandValidationError, parse_command_payload
from src.command_security import CommandVerifier, sign_command_envelope


class TestCommandSecurity(unittest.TestCase):
    """Command schema and security verifier tests."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = Ed25519PrivateKey.generate()
        cls.public_key_hex = cls.private_key.public_key().public_bytes_raw().hex()
        cls.private_key_hex = cls.private_key.private_bytes_raw().hex()

    def _security_config(self) -> dict:
        return {
            "device_id": "edge-agent-001",
            "require_signed_commands": True,
            "max_clock_skew_seconds": 300,
            "nonce_ttl_seconds": 900,
            "replay_store": {"type": "memory"},
            "trusted_signers": [
                {
                    "issuer": "control-plane",
                    "public_key_hex": self.public_key_hex,
                }
            ],
            "policy": {
                "allowed_actions": ["deploy"],
                "allowed_deployment_types": ["docker"],
                "allowed_images": ["nginx:*"],
            },
        }

    def _base_envelope(self) -> dict:
        return {
            "version": "1",
            "command_id": str(uuid.uuid4()),
            "timestamp": int(time.time()),
            "nonce": "nonce-12345678",
            "issuer": "control-plane",
            "device_id": "edge-agent-001",
            "action": "deploy",
            "params": {
                "type": "docker",
                "name": "web",
                "image": "nginx:latest",
            },
            "signature": "",
        }

    def _signed_payload(self, envelope: dict) -> str:
        signed = sign_command_envelope(envelope, self.private_key_hex)
        return json.dumps(signed)

    def test_parse_rejects_unknown_fields(self) -> None:
        envelope = self._base_envelope()
        envelope["unexpected"] = True
        with self.assertRaises(CommandValidationError):
            parse_command_payload(json.dumps(envelope))

    def test_verify_accepts_valid_signed_command(self) -> None:
        verifier = CommandVerifier(self._security_config())
        payload = self._signed_payload(self._base_envelope())
        command = verifier.verify_payload(payload)
        self.assertEqual(command.action, "deploy")
        self.assertEqual(command.params["image"], "nginx:latest")

    def test_verify_rejects_replay(self) -> None:
        verifier = CommandVerifier(self._security_config())
        envelope = self._base_envelope()
        payload = self._signed_payload(envelope)

        verifier.verify_payload(payload)
        with self.assertRaises(CommandValidationError):
            verifier.verify_payload(payload)

    def test_verify_rejects_wrong_device(self) -> None:
        verifier = CommandVerifier(self._security_config())
        envelope = self._base_envelope()
        envelope["device_id"] = "other-device"
        with self.assertRaises(CommandValidationError):
            verifier.verify_payload(self._signed_payload(envelope))

    def test_verify_rejects_disallowed_image(self) -> None:
        verifier = CommandVerifier(self._security_config())
        envelope = self._base_envelope()
        envelope["params"]["image"] = "malicious:latest"
        with self.assertRaises(CommandValidationError):
            verifier.verify_payload(self._signed_payload(envelope))

    def test_verify_rejects_invalid_signature(self) -> None:
        verifier = CommandVerifier(self._security_config())
        envelope = self._base_envelope()
        signed = sign_command_envelope(envelope, self.private_key_hex)
        signed["signature"] = "AAAA"
        with self.assertRaises(CommandValidationError):
            verifier.verify_payload(json.dumps(signed))


if __name__ == "__main__":
    unittest.main()
