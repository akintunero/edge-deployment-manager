#!/usr/bin/env python3
"""Generate internal CA and TLS certificates for edge deployment manager."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.pki.ca import DeviceCertificateAuthority


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PKI assets")
    parser.add_argument("--output-dir", default="certs", help="Output directory")
    parser.add_argument("--mqtt-cn", default="mqtt-broker", help="MQTT server certificate CN")
    parser.add_argument("--api-cn", default="control-plane", help="Control plane certificate CN")
    args = parser.parse_args()

    output = Path(args.output_dir)
    ca_cert = output / "ca.crt"
    ca_key = output / "ca.key"
    mqtt_cert = output / "mqtt-server.crt"
    mqtt_key = output / "mqtt-server.key"
    api_cert = output / "control-plane.crt"
    api_key = output / "control-plane.key"
    cp_mqtt_cert = output / "control-plane-mqtt.crt"
    cp_mqtt_key = output / "control-plane-mqtt.key"

    DeviceCertificateAuthority.generate_ca(ca_cert, ca_key)
    DeviceCertificateAuthority.generate_server_certificate(
        ca_cert,
        ca_key,
        mqtt_cert,
        mqtt_key,
        common_name=args.mqtt_cn,
        san_dns_names=("localhost", "mqtt-broker", "mosquitto"),
    )
    DeviceCertificateAuthority.generate_server_certificate(
        ca_cert,
        ca_key,
        api_cert,
        api_key,
        common_name=args.api_cn,
        san_dns_names=("localhost", "control-plane"),
    )
    DeviceCertificateAuthority.generate_client_certificate(
        ca_cert,
        ca_key,
        cp_mqtt_cert,
        cp_mqtt_key,
        common_name="edge-control-plane",
    )

    print(f"CA certificate: {ca_cert}")
    print(f"CA private key: {ca_key}")
    print(f"MQTT server certificate: {mqtt_cert}")
    print(f"MQTT server private key: {mqtt_key}")
    print(f"Control plane certificate: {api_cert}")
    print(f"Control plane private key: {api_key}")
    print(f"Control plane MQTT client certificate: {cp_mqtt_cert}")
    print(f"Control plane MQTT client private key: {cp_mqtt_key}")


if __name__ == "__main__":
    main()
