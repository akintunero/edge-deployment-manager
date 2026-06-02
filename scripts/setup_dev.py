#!/usr/bin/env python3
"""Generate local production-like credentials, configs, and environment."""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pki.ca import DeviceCertificateAuthority  # noqa: E402


def _write_env(path: Path, values: dict) -> None:
    lines = [f"{key}={value}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Setup local edge stack configuration")
    parser.add_argument("--output-dir", default=str(ROOT), help="Repository root")
    args = parser.parse_args()

    root = Path(args.output_dir)
    certs_dir = root / "certs"
    runtime_dir = root / "runtime"
    agent_cred_dir = runtime_dir / "agent-credentials"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    agent_cred_dir.mkdir(parents=True, exist_ok=True)

    ca_cert = certs_dir / "ca.crt"
    ca_key = certs_dir / "ca.key"
    DeviceCertificateAuthority.generate_ca(ca_cert, ca_key)
    DeviceCertificateAuthority.generate_server_certificate(
        ca_cert,
        ca_key,
        certs_dir / "mqtt-server.crt",
        certs_dir / "mqtt-server.key",
        common_name="mqtt-broker",
        san_dns_names=("localhost", "mqtt-broker"),
    )
    DeviceCertificateAuthority.generate_server_certificate(
        ca_cert,
        ca_key,
        certs_dir / "control-plane.crt",
        certs_dir / "control-plane.key",
        common_name="control-plane",
        san_dns_names=("localhost", "control-plane"),
    )
    DeviceCertificateAuthority.generate_client_certificate(
        ca_cert,
        ca_key,
        certs_dir / "control-plane-mqtt.crt",
        certs_dir / "control-plane-mqtt.key",
        common_name="edge-control-plane",
    )

    signing_key = Ed25519PrivateKey.generate()
    public_key_hex = signing_key.public_key().public_bytes_raw().hex()
    private_key_hex = signing_key.private_bytes_raw().hex()

    api_token = secrets.token_urlsafe(32)
    bootstrap_token = secrets.token_urlsafe(32)

    _write_env(
        root / ".env",
        {
            "CONTROL_PLANE_API_TOKEN": api_token,
            "EDGE_BOOTSTRAP_TOKEN": bootstrap_token,
            "EDGE_COMMAND_SIGNING_KEY_HEX": private_key_hex,
        },
    )

    control_plane_config = {
        "secrets": {"directory": "/run/secrets", "require_non_empty": False},
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
            "api_token_env": "CONTROL_PLANE_API_TOKEN",
            "rate_limit": {
                "enabled": True,
                "max_requests": 120,
                "window_seconds": 60,
            },
            "tls": {
                "enabled": True,
                "cert_file": "certs/control-plane.crt",
                "key_file": "certs/control-plane.key",
                "ca_cert": "certs/ca.crt",
                "require_client_cert": False,
            },
        },
        "logging": {"level": "INFO", "json": True},
        "signing": {"issuer": "control-plane", "private_key_env": "EDGE_COMMAND_SIGNING_KEY_HEX"},
        "mqtt": {
            "broker": "mosquitto",
            "port": 8883,
            "keepalive": 60,
            "client_id": "edge-control-plane",
            "command_topic": "edge/commands",
            "connect_timeout": 10,
            "tls": {
                "enabled": True,
                "ca_cert": "certs/ca.crt",
                "cert_file": "certs/control-plane-mqtt.crt",
                "key_file": "certs/control-plane-mqtt.key",
            },
        },
        "registry": {"backend": "sqlite", "path": "data/devices.db"},
        "audit": {"path": "data/audit.log"},
        "bootstrap": {
            "enabled": True,
            "token_env": "EDGE_BOOTSTRAP_TOKEN",
            "rate_limit": {
                "enabled": True,
                "max_requests": 10,
                "window_seconds": 60,
            },
            "cert_validity_days": 365,
            "pki": {"ca_cert": "certs/ca.crt", "ca_key": "certs/ca.key"},
            "credential_paths": {
                "ca_cert": "/etc/edge/ca.crt",
                "cert_file": "/etc/edge/agent.crt",
                "key_file": "/etc/edge/agent.key",
            },
            "default_policy": {
                "allowed_actions": ["deploy"],
                "allowed_deployment_types": ["docker"],
                "allowed_images": ["nginx:*"],
            },
            "agent_config_template": {
                "mqtt": {
                    "broker": "mosquitto",
                    "port": 8883,
                    "keepalive": 60,
                    "client_id": "edge-agent-001",
                    "topics": {
                        "commands": "edge/commands",
                        "deployments": "edge/deployments",
                        "status": "edge/status",
                        "logs": "edge/logs",
                    },
                    "tls": {"enabled": True},
                    "reconnect": {"initial_delay_seconds": 1, "max_delay_seconds": 30},
                },
                "security": {
                    "require_signed_commands": True,
                    "max_clock_skew_seconds": 300,
                    "nonce_ttl_seconds": 900,
                    "trusted_signers": [
                        {"issuer": "control-plane", "public_key_hex": public_key_hex}
                    ],
                },
                "deployment": {"enable_docker": True, "enable_kubernetes": False},
                "monitoring": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 9090,
                    "require_mqtt": True,
                },
                "logging": {"level": "INFO", "json": True},
            },
        },
    }

    agent_config = {
        "mqtt": {
            "broker": "mosquitto",
            "port": 8883,
            "keepalive": 60,
            "client_id": "edge-agent-001",
            "topics": {
                "commands": "edge/commands",
                "deployments": "edge/deployments",
                "status": "edge/status",
                "logs": "edge/logs",
            },
            "tls": {
                "enabled": True,
                "ca_cert": "/etc/edge/ca.crt",
                "cert_file": "/etc/edge/agent.crt",
                "key_file": "/etc/edge/agent.key",
            },
            "reconnect": {"initial_delay_seconds": 1, "max_delay_seconds": 30},
        },
        "deployment": {"enable_docker": True, "enable_kubernetes": False},
        "security": {
            "device_id": "edge-agent-001",
            "require_signed_commands": True,
            "max_clock_skew_seconds": 300,
            "nonce_ttl_seconds": 900,
            "replay_store": {
                "type": "sqlite",
                "path": "data/replay-nonces.db",
            },
            "trusted_signers": [
                {"issuer": "control-plane", "public_key_hex": public_key_hex}
            ],
            "policy": {
                "allowed_actions": ["deploy"],
                "allowed_deployment_types": ["docker"],
                "allowed_images": ["nginx:*"],
            },
        },
        "monitoring": {"enabled": True, "host": "0.0.0.0", "port": 9090, "require_mqtt": True},
        "logging": {"level": "INFO", "json": True},
    }

    runtime_cp = runtime_dir / "control-plane.yaml"
    runtime_agent = runtime_dir / "agent-config.yaml"
    runtime_cp.write_text(yaml.safe_dump(control_plane_config, sort_keys=False), encoding="utf-8")
    runtime_agent.write_text(yaml.safe_dump(agent_config, sort_keys=False), encoding="utf-8")

    print("Generated production-like local stack configuration:")
    print(f"  PKI directory: {certs_dir}")
    print(f"  Environment: {root / '.env'}")
    print(f"  Control plane config: {runtime_cp}")
    print(f"  Agent config template: {runtime_agent}")
    print("")
    print("Next:")
    print("  make prod-up")


if __name__ == "__main__":
    main()
