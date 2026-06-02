#!/usr/bin/env python3
"""
MQTT Handler for Edge Deployment Manager
Handles MQTT communication for deployment events and device synchronization
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import paho.mqtt.client as mqtt

from .command_envelope import CommandEnvelope, CommandValidationError
from .command_security import CommandVerifier
from .observability import METRICS
from .tls_config import configure_mqtt_client_tls, mqtt_port_with_tls

logger = logging.getLogger(__name__)


class MQTTHandler:
    """Handle MQTT communication for edge deployments"""

    connected: bool
    running: bool
    _loop_started: bool

    def __init__(
        self,
        config: Dict[str, Any],
        command_verifier: Optional[CommandVerifier] = None,
        on_valid_command: Optional[Callable[[CommandEnvelope], None]] = None,
    ):
        """Initialize MQTT handler with configuration"""
        self.broker = config.get("broker", "localhost")
        self.port = mqtt_port_with_tls(config)
        self.tls_config = config.get("tls", {})
        self.keepalive = config.get("keepalive", 60)
        self.client_id = config.get("client_id", "edge-deployment-manager")
        self.username = config.get("username")
        self.password = config.get("password")
        topics = config.get("topics", {})
        self.command_topic = topics.get("commands", "edge/commands")
        self._subscribe_topics = self._build_subscribe_topics(topics)

        reconnect_cfg = config.get("reconnect", {})
        self._reconnect_initial = float(reconnect_cfg.get("initial_delay_seconds", 1))
        self._reconnect_max = float(reconnect_cfg.get("max_delay_seconds", 60))

        self.command_verifier = command_verifier
        self.on_valid_command = on_valid_command

        self.connected = False
        self._loop_started = False
        self._reconnect_lock = threading.Lock()
        self.running = False

        self.message_handlers: Dict[str, Callable[[str], None]] = {}

        self.client = mqtt.Client(
            client_id=self.client_id,
            clean_session=True,
            protocol=mqtt.MQTTv311,
        )

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        self.client.on_publish = self._on_publish

        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        configure_mqtt_client_tls(self.client, self.tls_config)

        logger.info("MQTT handler configured for broker %s:%s", self.broker, self.port)

    @staticmethod
    def _build_subscribe_topics(topics: Dict[str, Any]) -> List[Tuple[str, int]]:
        return [
            (topics.get("deployments", "edge/deployments"), 1),
            (topics.get("status", "edge/status"), 1),
            (topics.get("commands", "edge/commands"), 1),
            (topics.get("logs", "edge/logs"), 0),
        ]

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Dict[str, Any],
        rc: int,
    ) -> None:
        if rc == 0:
            self.connected = True
            METRICS.set_gauge("edge_mqtt_connected", 1)
            logger.info("Connected to MQTT broker %s:%s", self.broker, self.port)
            self._subscribe_to_topics()
        else:
            self.connected = False
            METRICS.set_gauge("edge_mqtt_connected", 0)
            logger.error("MQTT connect failed with rc=%s", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        self.connected = False
        METRICS.set_gauge("edge_mqtt_connected", 0)
        if rc != 0:
            logger.warning("Unexpected MQTT disconnect rc=%s", rc)
            if self.running:
                self._schedule_reconnect()
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            topic = msg.topic
            message = msg.payload.decode("utf-8")

            if topic == self.command_topic and self.command_verifier is not None:
                self._handle_verified_command(message)
                return

            logger.info("Received MQTT message on topic '%s' (%d bytes)", topic, len(message))

            if topic in self.message_handlers:
                self.message_handlers[topic](message)
            else:
                self._handle_default_message(topic, message)

        except Exception as exc:
            logger.error("Error processing MQTT message: %s", exc)

    def _on_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        granted_qos: Tuple[int, ...],
    ) -> None:
        logger.debug("MQTT subscription confirmed qos=%s", granted_qos)

    def _on_publish(self, client: mqtt.Client, userdata: Any, mid: int) -> None:
        logger.debug("MQTT publish confirmed mid=%s", mid)

    def _subscribe_to_topics(self) -> None:
        for topic, qos in self._subscribe_topics:
            result, _mid = self.client.subscribe(topic, qos)
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info("Subscribed to topic %s (qos=%s)", topic, qos)
            else:
                logger.error("Failed to subscribe to topic %s", topic)

    def start(self) -> None:
        if self.running:
            logger.warning("MQTT handler is already running")
            return

        self.running = True
        logger.info("Starting MQTT handler")
        self._connect_with_wait()

    def stop(self) -> None:
        if not self.running:
            return

        logger.info("Stopping MQTT handler")
        self.running = False

        try:
            if self._loop_started:
                self.client.loop_stop()
                self._loop_started = False
            if self.connected:
                self.client.disconnect()
        except Exception as exc:
            logger.warning("Error during MQTT shutdown: %s", exc)

        self.connected = False
        METRICS.set_gauge("edge_mqtt_connected", 0)
        logger.info("MQTT handler stopped")

    def _wait_for_connection(self, attempts: int = 20, interval_seconds: float = 0.5) -> bool:
        for _ in range(attempts):
            if self.connected:
                return True
            time.sleep(interval_seconds)
        return False

    def _connect_with_wait(self) -> None:
        delay = self._reconnect_initial
        while self.running and not self.connected:
            try:
                if not self._loop_started:
                    self.client.connect(self.broker, self.port, self.keepalive)
                    self.client.loop_start()
                    self._loop_started = True

                if self._wait_for_connection():
                    logger.info("MQTT handler started successfully")
                    return
            except Exception as exc:
                logger.error("MQTT connect error: %s", exc)
                self._stop_loop()

            logger.warning("MQTT not connected; retrying in %ss", delay)
            time.sleep(delay)
            delay = min(delay * 2, self._reconnect_max)

        if not self.connected:
            logger.error("Failed to establish MQTT connection")

    def _schedule_reconnect(self) -> None:
        if not self._reconnect_lock.acquire(blocking=False):
            return
        threading.Thread(target=self._reconnect_loop, daemon=True).start()

    def _reconnect_loop(self) -> None:
        try:
            delay = self._reconnect_initial
            while self.running and not self.connected:
                try:
                    self._stop_loop()
                    self.client.reconnect()
                    if not self._loop_started:
                        self.client.loop_start()
                        self._loop_started = True

                    if self._wait_for_connection():
                        logger.info("MQTT reconnected")
                        return
                except Exception as exc:
                    logger.warning("MQTT reconnect failed: %s", exc)

                time.sleep(delay)
                delay = min(delay * 2, self._reconnect_max)
        finally:
            self._reconnect_lock.release()

    def _stop_loop(self) -> None:
        if self._loop_started:
            try:
                self.client.loop_stop()
            except Exception as exc:
                logger.debug("MQTT loop_stop failed during shutdown: %s", exc)
            self._loop_started = False

    def publish(self, topic: str, message: str, qos: int = 1, retain: bool = False) -> None:
        try:
            if not self.connected:
                logger.warning("Cannot publish - MQTT not connected")
                return

            result = self.client.publish(topic, message, qos=qos, retain=retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                METRICS.inc("edge_mqtt_messages_published_total")
                logger.info("Published message to '%s' (%d bytes)", topic, len(message))
            else:
                logger.error("Failed to publish to '%s' rc=%s", topic, result.rc)

        except Exception as exc:
            logger.error("Error publishing MQTT message: %s", exc)

    def register_handler(self, topic: str, handler: Callable[[str], None]) -> None:
        self.message_handlers[topic] = handler
        logger.info("Registered handler for topic %s", topic)

    def unregister_handler(self, topic: str) -> None:
        if topic in self.message_handlers:
            del self.message_handlers[topic]

    def _handle_default_message(self, topic: str, message: str) -> None:
        if topic == "edge/commands":
            self._handle_command(message)
        elif topic == "edge/deployments":
            self._handle_deployment_status(message)
        elif topic == "edge/status":
            self._handle_status_request(message)

    def _handle_verified_command(self, message: str) -> None:
        if self.command_verifier is None:
            logger.warning("Command verifier not configured; rejecting command")
            return

        try:
            envelope = self.command_verifier.verify_payload(message)
            METRICS.inc("edge_commands_accepted_total")
            logger.info(
                "Accepted command id=%s action=%s issuer=%s",
                envelope.command_id,
                envelope.action,
                envelope.issuer,
            )
            if self.on_valid_command:
                self.on_valid_command(envelope)
        except CommandValidationError as exc:
            METRICS.inc("edge_commands_rejected_total")
            logger.warning("Rejected command: %s", exc)
        except Exception as exc:
            METRICS.inc("edge_commands_failed_total")
            logger.error("Unexpected command handling error: %s", exc)

    def _handle_command(self, message: str) -> None:
        logger.info("Received legacy command payload (%d bytes)", len(message))

    def _handle_deployment_status(self, message: str) -> None:
        logger.info("Processing deployment status (%d bytes)", len(message))

    def _handle_status_request(self, message: str) -> None:
        logger.info("Processing status request (%d bytes)", len(message))

    def is_connected(self) -> bool:
        return self.connected

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "broker": self.broker,
            "port": self.port,
            "client_id": self.client_id,
            "running": self.running,
        }
