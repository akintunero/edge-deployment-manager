#!/usr/bin/env python3
"""Control plane entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from ..observability import configure_logging
from ..rate_limit import build_rate_limiter
from ..secrets import SecretProvider
from ..tls_config import create_server_ssl_context
from .api import ControlPlaneHttpServer
from .audit import AuditLog
from .bootstrap import build_bootstrap_service
from .ha import build_leader_elector
from .leader_election import LeaderElector
from .mqtt_publisher import MqttCommandPublisher
from .registry_factory import RegistryBackend, build_device_registry
from .service import ControlPlaneService

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("control plane configuration root must be a mapping")
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge deployment control plane API")
    parser.add_argument(
        "--config",
        default="configs/control-plane.yaml",
        help="Path to control plane configuration file",
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        configure_logging(config.get("logging", {"level": "INFO"}))
        server_cfg = config.get("server", {})
        host = server_cfg.get("host", "127.0.0.1")
        port = int(server_cfg.get("port", 8080))

        secret_provider = SecretProvider.from_config(config.get("secrets", {}))
        token_env = str(server_cfg.get("api_token_env", "CONTROL_PLANE_API_TOKEN"))
        api_token = secret_provider.get(token_env)

        registry_cfg = config.get("registry", {})
        audit_path = Path(config.get("audit", {}).get("path", "data/audit.log"))

        registry: RegistryBackend = build_device_registry(registry_cfg, secret_provider)
        leader_elector: Optional[LeaderElector] = build_leader_elector(
            config,
            registry_cfg,
            secret_provider,
        )
        audit = AuditLog(audit_path)
        mqtt = MqttCommandPublisher(config.get("mqtt", {}))
        service = ControlPlaneService(
            registry=registry,
            mqtt_publisher=mqtt,
            audit_log=audit,
            signing_config=config.get("signing", {}),
            secret_provider=secret_provider,
            leader_elector=leader_elector,
        )

        bootstrap_service = None
        bootstrap_cfg = config.get("bootstrap", {})
        if bootstrap_cfg.get("enabled", False):
            bootstrap_service = build_bootstrap_service(
                bootstrap_cfg,
                registry,
                audit,
                secret_provider,
            )

        def readiness_check() -> Dict[str, Any]:
            is_leader = leader_elector.is_leader if leader_elector is not None else True
            return {
                "ready": True,
                "checks": {
                    "devices_registered": len(registry.list_devices()),
                    "bootstrap_enabled": bootstrap_cfg.get("enabled", False),
                    "is_leader": is_leader,
                    "leader_holder": (leader_elector.holder_id if leader_elector is not None else None),
                },
            }

        bootstrap_rate_limiter = build_rate_limiter(bootstrap_cfg.get("rate_limit"))
        api_rate_limiter = build_rate_limiter(server_cfg.get("rate_limit"))

        httpd = ControlPlaneHttpServer(
            (host, port),
            registry=registry,
            service=service,
            audit=audit,
            api_token=api_token,
            bootstrap_service=bootstrap_service,
            bootstrap_rate_limiter=bootstrap_rate_limiter,
            api_rate_limiter=api_rate_limiter,
            leader_elector=leader_elector,
            readiness_check=readiness_check,
        )

        tls_cfg = server_cfg.get("tls", {})
        scheme = "http"
        if tls_cfg.get("enabled"):
            ssl_context = create_server_ssl_context(tls_cfg)
            httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
            scheme = "https"

        logger.info("Control plane listening on %s://%s:%s", scheme, host, port)
        try:
            httpd.serve_forever()
        finally:
            if leader_elector is not None:
                leader_elector.stop()
    except KeyboardInterrupt:
        logger.info("Control plane shutdown requested")
    except Exception as exc:
        logger.error("Control plane failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
