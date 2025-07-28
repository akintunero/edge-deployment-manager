#!/usr/bin/env python3
"""
MQTT Handler for Edge Deployment Manager
Handles MQTT communication for deployment events and device synchronization
"""

import paho.mqtt.client as mqtt
import logging
import threading
import time
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)


class MQTTHandler:
    """Handles MQTT communication for edge deployment events"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.broker = config.get("broker", "localhost")
        self.port = config.get("port", 1883)
        self.keepalive = config.get("keepalive", 60)
        self.client_id = config.get("client_id", "edge-deployment-manager")

        # Initialize MQTT client with modern API
        self.client = mqtt.Client(client_id=self.client_id, clean_session=True, protocol=mqtt.MQTTv311)

        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
        self.client.on_subscribe = self._on_subscribe

        # Connection state
        self.connected = False
        self.connection_thread = None

        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}

        logger.info(f"MQTT Handler initialized for broker: {self.broker}:{self.port}")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.connected = True
            logger.info("Successfully connected to MQTT broker")

            # Subscribe to deployment topics
            self._subscribe_to_topics()
        else:
            logger.error(f"Failed to connect to MQTT broker with code: {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker with code: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_message(self, client, userdata, msg):
        """Callback when message is received"""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")
            logger.info(f"Received message on topic {topic}: {payload}")

            # Handle message based on topic
            if topic in self.message_handlers:
                self.message_handlers[topic](payload)
            else:
                logger.debug(f"No handler registered for topic: {topic}")

        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")

    def _on_publish(self, client, userdata, mid):
        """Callback when message is published"""
        logger.debug(f"Message published with ID: {mid}")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback when subscription is successful"""
        logger.info(f"Successfully subscribed with QoS: {granted_qos}")

    def _subscribe_to_topics(self):
        """Subscribe to relevant deployment topics"""
        topics = [("edge/deployments", 1), ("edge/status", 1), ("edge/commands", 1), ("edge/logs", 0)]

        for topic, qos in topics:
            try:
                result = self.client.subscribe(topic, qos)
                if result[0] == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"Subscribed to topic: {topic} with QoS: {qos}")
                else:
                    logger.error(f"Failed to subscribe to topic: {topic}")
            except Exception as e:
                logger.error(f"Error subscribing to topic {topic}: {e}")

    def start(self):
        """Start MQTT client connection"""
        try:
            logger.info("Starting MQTT client...")

            # Connect to broker
            self.client.connect(self.broker, self.port, self.keepalive)

            # Start the network loop in a separate thread
            self.connection_thread = threading.Thread(target=self._network_loop, daemon=True)
            self.connection_thread.start()

            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if not self.connected:
                logger.error("Failed to connect to MQTT broker within timeout")
                return False

            logger.info("MQTT client started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting MQTT client: {e}")
            return False

    def _network_loop(self):
        """Network loop for MQTT client"""
        try:
            self.client.loop_forever()
        except Exception as e:
            logger.error(f"Error in MQTT network loop: {e}")

    def stop(self):
        """Stop MQTT client"""
        try:
            logger.info("Stopping MQTT client...")
            self.client.disconnect()
            self.client.loop_stop()
            logger.info("MQTT client stopped")
        except Exception as e:
            logger.error(f"Error stopping MQTT client: {e}")

    def publish(self, topic: str, message: str, qos: int = 1, retain: bool = False):
        """Publish message to MQTT topic"""
        try:
            if not self.connected:
                logger.warning("Cannot publish: MQTT client not connected")
                return False

            result = self.client.publish(topic, message, qos=qos, retain=retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Message published to {topic}: {message}")
                return True
            else:
                logger.error(f"Failed to publish message to {topic}")
                return False

        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False

    def register_handler(self, topic: str, handler: Callable):
        """Register a message handler for a specific topic"""
        self.message_handlers[topic] = handler
        logger.info(f"Registered handler for topic: {topic}")

    def is_connected(self) -> bool:
        """Check if MQTT client is connected"""
        return self.connected
