#!/usr/bin/env python3
"""TLS configuration helpers for MQTT clients and HTTP servers."""

from __future__ import annotations

import ssl
from pathlib import Path
from typing import Any, Dict

import paho.mqtt.client as mqtt


class TlsConfigError(ValueError):
    """Raised when TLS settings are invalid."""


def expand_path(path: str) -> str:
    return str(Path(path).expanduser())


def create_server_ssl_context(tls_config: Dict[str, Any]) -> ssl.SSLContext:
    """Build TLS context for the control plane HTTP server."""
    if not tls_config.get("enabled"):
        raise TlsConfigError("TLS is not enabled in server configuration")

    cert_file = expand_path(tls_config["cert_file"])
    key_file = expand_path(tls_config["key_file"])

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)

    if tls_config.get("require_client_cert"):
        ca_cert = expand_path(tls_config["ca_cert"])
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cafile=ca_cert)
    else:
        context.verify_mode = ssl.CERT_NONE

    return context


def configure_mqtt_client_tls(client: mqtt.Client, tls_config: Dict[str, Any]) -> None:
    """Apply TLS/mTLS settings to a Paho MQTT client."""
    if not tls_config or not tls_config.get("enabled"):
        return

    ca_cert = tls_config.get("ca_cert")
    cert_file = tls_config.get("cert_file")
    key_file = tls_config.get("key_file")
    insecure = bool(tls_config.get("insecure", False))

    if ca_cert:
        ca_cert = expand_path(ca_cert)
    if cert_file:
        cert_file = expand_path(cert_file)
    if key_file:
        key_file = expand_path(key_file)

    client.tls_set(
        ca_certs=ca_cert,
        certfile=cert_file,
        keyfile=key_file,
        cert_reqs=ssl.CERT_NONE if insecure else ssl.CERT_REQUIRED,
    )
    if insecure:
        client.tls_insecure_set(True)


def mqtt_port_with_tls(config: Dict[str, Any]) -> int:
    """Return MQTT port, defaulting to 8883 when TLS is enabled."""
    port = int(config.get("port", 1883))
    tls_config = config.get("tls", {})
    if tls_config.get("enabled") and port == 1883:
        return int(tls_config.get("port", 8883))
    return port
