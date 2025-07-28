#!/usr/bin/env python3
"""
Edge Deployment Manager
=======================

Main deployment manager for edge computing environments.
Orchestrates Docker containers, Kubernetes deployments, and MQTT communication.
"""

import sys
import yaml
import logging
import threading
from typing import Dict, Any, Optional

# Import handlers
from .mqtt_handler import MQTTHandler
from .docker_handler import DockerHandler
from .k8s_controller import KubernetesController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class EdgeDeploymentManager:
    """Main orchestration class for edge deployments"""

    def __init__(self, config_path: str = "configs/config.yaml"):
        """Initialize the deployment manager"""
        self.config_path = config_path
        self.config = self.load_config()

        # Initialize handlers (will be set during service initialization)
        self.mqtt_handler: Optional[MQTTHandler] = None
        self.docker_handler: Optional[DockerHandler] = None
        self.k8s_controller: Optional[KubernetesController] = None

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, "r") as file:
                config = yaml.safe_load(file)
                logger.info(f"Configuration loaded from {self.config_path}")
                return config
        except FileNotFoundError:
            error_msg = f"Configuration file not found: {self.config_path}"
            logger.error(error_msg)
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            raise

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
            # Re-raise the exception instead of calling sys.exit
            # for better testing
            raise RuntimeError(f"Failed to initialize services: {e}") from e

    def start(self):
        """Start the deployment manager"""
        try:
            logger.info("Starting Edge Deployment Manager...")

            # Initialize all services
            self.initialize_services()

            # Start MQTT handler if configured
            if self.mqtt_handler:
                self.mqtt_handler.start()
                logger.info("MQTT communication started")

            logger.info("Edge Deployment Manager started successfully")

        except Exception as e:
            logger.error(f"Error starting deployment manager: {e}")
            raise

    def stop(self):
        """Stop the deployment manager"""
        try:
            logger.info("Stopping Edge Deployment Manager...")

            # Stop MQTT handler
            if self.mqtt_handler:
                self.mqtt_handler.stop()
                logger.info("MQTT communication stopped")

            logger.info("Edge Deployment Manager stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping deployment manager: {e}")

    def deploy_application(self, app_config: Dict[str, Any]) -> bool:
        """Deploy an application using the specified configuration"""
        try:
            deployment_type = app_config.get("type", "docker")
            app_name = app_config.get("name", "unknown")

            logger.info(
                f"Deploying application: {app_name} "
                f"(type: {deployment_type})"
            )

            if deployment_type == "docker":
                return self._deploy_docker_app(app_config)
            elif deployment_type == "kubernetes":
                return self._deploy_k8s_app(app_config)
            else:
                logger.error(f"Unsupported deployment type: {deployment_type}")
                return False

        except Exception as e:
            logger.error(f"Error deploying application: {e}")
            return False

    def _deploy_docker_app(self, app_config: Dict[str, Any]) -> bool:
        """Deploy a Docker application"""
        try:
            if not self.docker_handler:
                logger.error("Docker handler not initialized")
                return False

            container_id = self.docker_handler.deploy_container(app_config)

            if container_id:
                logger.info(f"Docker application deployed: {container_id}")

                # Publish deployment status via MQTT
                if self.mqtt_handler:
                    message = {
                        "type": "deployment",
                        "status": "success",
                        "container_id": container_id,
                        "application": app_config.get("name"),
                    }
                    self.mqtt_handler.publish("edge/deployments", str(message))

                return True
            else:
                logger.error("Failed to deploy Docker application")
                return False

        except Exception as e:
            logger.error(f"Error deploying Docker application: {e}")
            return False

    def _deploy_k8s_app(self, app_config: Dict[str, Any]) -> bool:
        """Deploy a Kubernetes application"""
        try:
            if not self.k8s_controller:
                logger.error("Kubernetes controller not initialized")
                return False

            yaml_file = app_config.get("yaml_file")
            namespace = app_config.get("namespace", "default")

            if not yaml_file:
                logger.error(
                    "No YAML file specified for Kubernetes " "deployment"
                )
                return False

            success = self.k8s_controller.deploy_from_yaml(
                yaml_file, namespace
            )

            if success:
                logger.info("Kubernetes application deployed successfully")

                # Publish deployment status via MQTT
                if self.mqtt_handler:
                    message = {
                        "type": "deployment",
                        "status": "success",
                        "platform": "kubernetes",
                        "namespace": namespace,
                        "application": app_config.get("name"),
                    }
                    self.mqtt_handler.publish("edge/deployments", str(message))

                return True
            else:
                logger.error("Failed to deploy Kubernetes application")
                return False

        except Exception as e:
            logger.error(f"Error deploying Kubernetes application: {e}")
            return False


def main():
    """Main entry point"""
    try:
        # Initialize deployment manager
        manager = EdgeDeploymentManager()

        # Start the manager
        manager.start()

        # Keep the application running
        try:
            while True:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")

        # Stop the manager
        manager.stop()

    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
