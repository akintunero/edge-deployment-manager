#!/usr/bin/env python3
"""
MQTT Handler for Edge Deployment Manager
Handles MQTT communication for deployment events and device synchronization
"""

import paho.mqtt.client as mqtt
import logging
import threading
import time
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)


class MQTTHandler:
    """Handle MQTT communication for edge deployments"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize MQTT handler with configuration"""
        self.broker = config.get("broker", "localhost")
        self.port = config.get("port", 1883)
        self.keepalive = config.get("keepalive", 60)
        self.client_id = config.get("client_id", "edge-deployment-manager")
        self.username = config.get("username")
        self.password = config.get("password")

        # Connection state
        self.connected = False
        self.connection_thread = None
        self.running = False

        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}

        # Initialize MQTT client
        self.client = mqtt.Client(
            client_id=self.client_id,
            clean_session=True,
            protocol=mqtt.MQTTv311
        )

        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        self.client.on_publish = self._on_publish

        # Set authentication if provided
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        broker_info = f"{self.broker}:{self.port}"
        logger.info(f"MQTT Handler initialized for broker: {broker_info}")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when client connects to broker"""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker: {self.broker}:{self.port}")
            self._subscribe_to_topics()
        else:
            logger.error("Failed to connect to MQTT broker. "
                        f"Return code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when client disconnects from broker"""
        self.connected = False
        if rc != 0:
            disconnect_msg = ("Unexpected disconnection from MQTT broker "
                            f"with code: {rc}")
            logger.warning(disconnect_msg)
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_message(self, client, userdata, msg):
        """Callback for when a message is received"""
        try:
            topic = msg.topic
            message = msg.payload.decode('utf-8')

            logger.info(f"Received message on topic '{topic}': {message}")

            # Check if we have a handler for this topic
            if topic in self.message_handlers:
                self.message_handlers[topic](message)
            else:
                # Default handling for common topics
                self._handle_default_message(topic, message)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback for when client subscribes to a topic"""
        logger.debug(f"Subscription confirmed with QoS: {granted_qos}")

    def _on_publish(self, client, userdata, mid):
        """Callback for when a message is published"""
        logger.debug(f"Message published with ID: {mid}")

    def _subscribe_to_topics(self):
        """Subscribe to default topics"""
        default_topics = [
            ("edge/deployments", 1),
            ("edge/status", 1),
            ("edge/commands", 1),
            ("edge/logs", 0)
        ]

        for topic, qos in default_topics:
            result, mid = self.client.subscribe(topic, qos)
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Subscribed to topic: {topic} with QoS: {qos}")
            else:
                logger.error(f"Failed to subscribe to topic: {topic}")

    def start(self):
        """Start MQTT client connection"""
        try:
            if self.running:
                logger.warning("MQTT handler is already running")
                return

            self.running = True
            logger.info("Starting MQTT handler...")

            # Start connection in a separate thread
            self.connection_thread = threading.Thread(
                target=self._network_loop, daemon=True)
            self.connection_thread.start()

            # Wait for connection
            retry_count = 0
            max_retries = 10

            while not self.connected and retry_count < max_retries:
                time.sleep(1)
                retry_count += 1

            if self.connected:
                logger.info("MQTT handler started successfully")
            else:
                logger.error("Failed to establish MQTT connection")

        except Exception as e:
            logger.error(f"Error starting MQTT handler: {e}")

    def stop(self):
        """Stop MQTT client connection"""
        try:
            if not self.running:
                logger.warning("MQTT handler is not running")
                return

            logger.info("Stopping MQTT handler...")
            self.running = False

            if self.client and self.connected:
                self.client.disconnect()

            if self.connection_thread:
                self.connection_thread.join(timeout=5)

            logger.info("MQTT handler stopped")

        except Exception as e:
            logger.error(f"Error stopping MQTT handler: {e}")

    def _network_loop(self):
        """Network loop for MQTT client"""
        try:
            self.client.connect(self.broker, self.port, self.keepalive)
            self.client.loop_forever()
        except Exception as e:
            logger.error(f"Error in MQTT network loop: {e}")

    def publish(self, topic: str, message: str, qos: int = 1,
                retain: bool = False):
        """Publish a message to a topic"""
        try:
            if not self.connected:
                logger.warning("Cannot publish - not connected to MQTT broker")
                return

            result = self.client.publish(
                topic, message, qos=qos, retain=retain)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published message to '{topic}': {message}")
            else:
                logger.error(f"Failed to publish message to '{topic}'")

        except Exception as e:
            logger.error(f"Error publishing message: {e}")

    def register_handler(self, topic: str, handler: Callable[[str], None]):
        """Register a message handler for a specific topic"""
        self.message_handlers[topic] = handler
        logger.info(f"Registered handler for topic: {topic}")

    def unregister_handler(self, topic: str):
        """Unregister a message handler for a topic"""
        if topic in self.message_handlers:
            del self.message_handlers[topic]
            logger.info(f"Unregistered handler for topic: {topic}")

    def _handle_default_message(self, topic: str, message: str):
        """Handle messages for topics without specific handlers"""
        if topic == "edge/commands":
            self._handle_command(message)
        elif topic == "edge/deployments":
            self._handle_deployment_status(message)
        elif topic == "edge/status":
            self._handle_status_request(message)
        else:
            logger.info(f"No specific handler for topic '{topic}': {message}")

    def _handle_command(self, message: str):
        """Handle command messages"""
        try:
            logger.info(f"Processing command: {message}")
            # Add command processing logic here
        except Exception as e:
            logger.error(f"Error handling command: {e}")

    def _handle_deployment_status(self, message: str):
        """Handle deployment status messages"""
        try:
            logger.info(f"Processing deployment status: {message}")
            # Add deployment status processing logic here
        except Exception as e:
            logger.error(f"Error handling deployment status: {e}")

    def _handle_status_request(self, message: str):
        """Handle status request messages"""
        try:
            logger.info(f"Processing status request: {message}")
            # Add status request processing logic here
        except Exception as e:
            logger.error(f"Error handling status request: {e}")

    def is_connected(self) -> bool:
        """Check if client is connected to broker"""
        return self.connected

    def get_status(self) -> Dict[str, Any]:
        """Get MQTT handler status"""
        return {
            "connected": self.connected,
            "broker": self.broker,
            "port": self.port,
            "client_id": self.client_id,
            "running": self.running
        }
