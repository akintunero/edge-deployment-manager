#!/usr/bin/env python3
"""Publish signed commands to the MQTT broker."""

from __future__ import annotations

import logging
from typing import Any, Dict

import paho.mqtt.client as mqtt

from ..tls_config import configure_mqtt_client_tls, mqtt_port_with_tls

logger = logging.getLogger(__name__)


class MqttPublishError(RuntimeError):
    """Raised when MQTT publish fails."""


class MqttCommandPublisher:
    """Synchronous MQTT publisher for signed command envelopes."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._broker = config.get("broker", "localhost")
        self._port = mqtt_port_with_tls(config)
        self._tls_config = config.get("tls", {})
        self._keepalive = int(config.get("keepalive", 60))
        self._command_topic = str(config.get("command_topic", "edge/commands"))
        self._client_id = config.get("client_id", "edge-control-plane")
        self._username = config.get("username")
        self._password = config.get("password")
        self._connect_timeout = int(config.get("connect_timeout", 10))

    @property
    def command_topic(self) -> str:
        return self._command_topic

    def publish_command(self, payload: str) -> None:
        client = mqtt.Client(
            client_id=self._client_id,
            clean_session=True,
            protocol=mqtt.MQTTv311,
        )
        if self._username and self._password:
            client.username_pw_set(self._username, self._password)

        configure_mqtt_client_tls(client, self._tls_config)

        try:
            client.connect(self._broker, self._port, self._keepalive)
            client.loop_start()
            result = client.publish(self._command_topic, payload, qos=1)
            result.wait_for_publish(timeout=self._connect_timeout)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise MqttPublishError(f"publish failed with code {result.rc}")
            logger.info(
                "Published command to topic '%s' (%d bytes)",
                self._command_topic,
                len(payload),
            )
        except Exception as exc:
            raise MqttPublishError(str(exc)) from exc
        finally:
            client.loop_stop()
            client.disconnect()
