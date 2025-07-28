#!/usr/bin/env python3
"""
Edge Deployment Manager - Main entry point
Handles initialization and coordination of edge deployment services
"""

import yaml
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Import our handlers
from mqtt_handler import MQTTHandler
from docker_handler import DockerHandler
from k8s_controller import KubernetesController

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class EdgeDeploymentManager:
    """Main manager class for edge deployment operations"""

    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.mqtt_handler = None
        self.docker_handler = None
        self.k8s_controller = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.error(f"Configuration file not found: {self.config_path}")
                sys.exit(1)

            with open(config_file, "r") as file:
                config = yaml.safe_load(file)
                logger.info(f"Configuration loaded from {self.config_path}")
                return config
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            sys.exit(1)

    def initialize_services(self):
        """Initialize all deployment services"""
        try:
            logger.info("Initializing Edge Deployment Manager services...")

            # Initialize MQTT handler
            if self.config.get("mqtt"):
                self.mqtt_handler = MQTTHandler(self.config["mqtt"])
                logger.info("MQTT handler initialized")

            # Initialize Docker handler
            self.docker_handler = DockerHandler()
            logger.info("Docker handler initialized")

            # Initialize Kubernetes controller
            self.k8s_controller = KubernetesController()
            logger.info("Kubernetes controller initialized")

            logger.info("All services initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            # Re-raise the exception instead of calling sys.exit for better testing
            raise RuntimeError(f"Failed to initialize services: {e}") from e

    def start(self):
        """Start the deployment manager"""
        try:
            logger.info("Starting Edge Deployment Manager...")
            self.initialize_services()

            # Start MQTT client if available
            if self.mqtt_handler:
                self.mqtt_handler.start()

            logger.info("Edge Deployment Manager is running")

            # Keep the manager running
            try:
                while True:
                    import time

                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down Edge Deployment Manager...")
                self.shutdown()

        except Exception as e:
            logger.error(f"Error starting deployment manager: {e}")
            sys.exit(1)

    def shutdown(self):
        """Gracefully shutdown all services"""
        try:
            logger.info("Shutting down services...")

            if self.mqtt_handler:
                self.mqtt_handler.stop()

            logger.info("Edge Deployment Manager shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def main():
    """Main entry point"""
    try:
        manager = EdgeDeploymentManager()
        manager.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
