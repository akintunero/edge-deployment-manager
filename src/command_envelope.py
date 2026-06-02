#!/usr/bin/env python3
"""Strict command envelope parsing for MQTT control-plane messages."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Mapping

ENVELOPE_VERSION = "1"
MAX_PAYLOAD_BYTES = 64 * 1024

ALLOWED_TOP_LEVEL_KEYS: FrozenSet[str] = frozenset(
    {
        "version",
        "command_id",
        "timestamp",
        "nonce",
        "issuer",
        "device_id",
        "action",
        "params",
        "signature",
    }
)

ALLOWED_ACTIONS: FrozenSet[str] = frozenset({"deploy"})
ALLOWED_DEPLOY_PARAM_KEYS: FrozenSet[str] = frozenset(
    {
        "type",
        "name",
        "image",
        "ports",
        "environment",
        "volumes",
        "command",
        "working_dir",
        "yaml_file",
        "namespace",
        "restart_policy",
        "remove",
    }
)

COMMAND_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
NONCE_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


class CommandValidationError(ValueError):
    """Raised when an inbound command fails schema or policy checks."""


@dataclass(frozen=True)
class CommandEnvelope:
    """Validated command envelope accepted at the MQTT boundary."""

    version: str
    command_id: str
    timestamp: int
    nonce: str
    issuer: str
    device_id: str
    action: str
    params: Dict[str, Any]
    signature: str
    raw: Dict[str, Any]


def parse_command_payload(payload: str) -> CommandEnvelope:
    """Parse and strictly validate a JSON command envelope."""
    if len(payload.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise CommandValidationError("command payload exceeds size limit")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise CommandValidationError("command payload is not valid JSON") from exc

    if not isinstance(data, dict):
        raise CommandValidationError("command payload must be a JSON object")

    unknown_keys = set(data.keys()) - ALLOWED_TOP_LEVEL_KEYS
    if unknown_keys:
        raise CommandValidationError(f"unknown envelope fields: {', '.join(sorted(unknown_keys))}")

    missing = ALLOWED_TOP_LEVEL_KEYS - set(data.keys())
    if missing:
        raise CommandValidationError(f"missing required envelope fields: {', '.join(sorted(missing))}")

    version = _require_str(data, "version")
    if version != ENVELOPE_VERSION:
        raise CommandValidationError(f"unsupported envelope version: {version}")

    command_id = _require_str(data, "command_id")
    if not COMMAND_ID_PATTERN.match(command_id):
        raise CommandValidationError("command_id must be a UUID string")

    timestamp = data["timestamp"]
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise CommandValidationError("timestamp must be an integer unix epoch")
    if timestamp <= 0:
        raise CommandValidationError("timestamp must be positive")

    nonce = _require_str(data, "nonce")
    if not NONCE_PATTERN.match(nonce):
        raise CommandValidationError("nonce format is invalid")

    issuer = _require_str(data, "issuer")
    device_id = _require_str(data, "device_id")
    action = _require_str(data, "action")
    if action not in ALLOWED_ACTIONS:
        raise CommandValidationError(f"unsupported action: {action}")

    signature = _require_str(data, "signature")
    params = data["params"]
    if not isinstance(params, dict):
        raise CommandValidationError("params must be an object")

    _validate_deploy_params(params, action)

    return CommandEnvelope(
        version=version,
        command_id=command_id,
        timestamp=timestamp,
        nonce=nonce,
        issuer=issuer,
        device_id=device_id,
        action=action,
        params=dict(params),
        signature=signature,
        raw=dict(data),
    )


def canonical_signing_bytes(envelope: Mapping[str, Any]) -> bytes:
    """Return canonical bytes used for Ed25519 signatures."""
    signing_body = {key: envelope[key] for key in sorted(envelope) if key != "signature"}
    return json.dumps(signing_body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _validate_deploy_params(params: Dict[str, Any], action: str) -> None:
    if action != "deploy":
        return

    unknown = set(params.keys()) - ALLOWED_DEPLOY_PARAM_KEYS
    if unknown:
        raise CommandValidationError(f"unknown deploy params: {', '.join(sorted(unknown))}")

    deployment_type = params.get("type", "docker")
    if deployment_type not in {"docker", "kubernetes"}:
        raise CommandValidationError("deploy type must be docker or kubernetes")

    name = params.get("name")
    if name is not None and not isinstance(name, str):
        raise CommandValidationError("deploy name must be a string")

    if deployment_type == "docker":
        image = params.get("image")
        if not isinstance(image, str) or not image.strip():
            raise CommandValidationError("docker deploy requires image")
    else:
        yaml_file = params.get("yaml_file")
        if not isinstance(yaml_file, str) or not yaml_file.strip():
            raise CommandValidationError("kubernetes deploy requires yaml_file")


def _require_str(data: Dict[str, Any], field: str) -> str:
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        raise CommandValidationError(f"{field} must be a non-empty string")
    return value.strip()
