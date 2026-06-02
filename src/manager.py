#!/usr/bin/env python3
"""
Edge Deployment Manager
=======================

Main deployment manager for edge computing environments.
Orchestrates Docker containers, Kubernetes deployments, and MQTT communication.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
from typing import Any, Dict, Optional

import yaml

from .command_envelope import CommandEnvelope
from .command_security import CommandVerifier, build_command_verifier
from .docker_handler import DockerHandler
from .health_server import HealthServer
from .k8s_controller import KubernetesController
from .mqtt_handler import MQTTHandler
from .observability import METRICS, configure_logging

logger = logging.getLogger(__name__)


class EdgeDeploymentManager:
    """Main orchestration class for edge deployments"""

    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
        configure_logging(self.config.get("logging", {}))

        self.mqtt_handler: Optional[MQTTHandler] = None
        self.docker_handler: Optional[DockerHandler] = None
        self.k8s_controller: Optional[KubernetesController] = None
        self.command_verifier: Optional[CommandVerifier] = None
        self.health_server: Optional[HealthServer] = None

    def load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)
                if not isinstance(config, dict):
                    raise ValueError("configuration root must be a mapping")
                logger.info("Configuration loaded from %s", self.config_path)
                return config
        except FileNotFoundError:
            logger.error("Configuration file not found: %s", self.config_path)
            raise
        except yaml.YAMLError as exc:
            logger.error("Error parsing configuration file: %s", exc)
            raise

    def initialize_services(self) -> None:
        logger.info("Initializing Edge Deployment Manager services")

        self.command_verifier = build_command_verifier(self.config)

        if self.config.get("mqtt"):
            self.mqtt_handler = MQTTHandler(
                self.config["mqtt"],
                command_verifier=self.command_verifier,
                on_valid_command=self._on_valid_command,
            )
            if self.command_verifier:
                logger.info("MQTT handler initialized with signed command verification")
            else:
                logger.warning(
                    "MQTT handler initialized without security config; " "commands are not cryptographically verified"
                )

        deployment_cfg = self.config.get("deployment", {})
        if deployment_cfg.get("enable_docker", True):
            self.docker_handler = self._init_docker_handler()

        if deployment_cfg.get("enable_kubernetes", False):
            self.k8s_controller = self._init_kubernetes_controller()

        monitoring = self.config.get("monitoring", {})
        if monitoring.get("enabled", False):
            host = monitoring.get("host", "127.0.0.1")
            port = int(monitoring.get("port", 9090))
            self.health_server = HealthServer(host, port, self.readiness)
            self.health_server.start()

        logger.info("Service initialization complete")

    @staticmethod
    def _init_docker_handler() -> Optional[DockerHandler]:
        try:
            handler = DockerHandler()
            logger.info("Docker handler initialized")
            return handler
        except Exception as exc:
            logger.warning("Docker handler unavailable: %s", exc)
            return None

    @staticmethod
    def _init_kubernetes_controller() -> Optional[KubernetesController]:
        try:
            controller = KubernetesController()
            logger.info("Kubernetes controller initialized")
            return controller
        except Exception as exc:
            logger.warning("Kubernetes controller unavailable: %s", exc)
            return None

    def readiness(self) -> Dict[str, Any]:
        checks: Dict[str, Any] = {}
        ready = True

        if self.mqtt_handler is not None:
            mqtt_ok = self.mqtt_handler.is_connected()
            checks["mqtt_connected"] = mqtt_ok
            if self.config.get("monitoring", {}).get("require_mqtt", True):
                ready = ready and mqtt_ok

        checks["docker_available"] = self.docker_handler is not None
        checks["kubernetes_available"] = self.k8s_controller is not None

        return {"ready": ready, "checks": checks}

    def start(self) -> None:
        logger.info("Starting Edge Deployment Manager")
        self.initialize_services()

        if self.mqtt_handler:
            self.mqtt_handler.start()
            logger.info("MQTT communication started")

        logger.info("Edge Deployment Manager started successfully")

    def stop(self) -> None:
        logger.info("Stopping Edge Deployment Manager")

        if self.health_server:
            self.health_server.stop()

        if self.mqtt_handler:
            self.mqtt_handler.stop()
            logger.info("MQTT communication stopped")

        logger.info("Edge Deployment Manager stopped")

    def _on_valid_command(self, envelope: CommandEnvelope) -> None:
        if envelope.action == "deploy":
            success = self.deploy_application(envelope.params)
            METRICS.inc("edge_commands_processed_total")
            if success:
                METRICS.inc("edge_deployments_success_total")
            else:
                METRICS.inc("edge_deployments_failed_total")
            self._publish_command_result(envelope, success)
            return

        logger.error("No handler for verified action: %s", envelope.action)

    def _publish_command_result(self, envelope: CommandEnvelope, success: bool) -> None:
        if not self.mqtt_handler:
            return

        status_topic = self.config.get("mqtt", {}).get("topics", {}).get("deployments", "edge/deployments")
        payload = {
            "command_id": envelope.command_id,
            "status": "success" if success else "failed",
            "action": envelope.action,
            "device_id": envelope.device_id,
        }
        self.mqtt_handler.publish(status_topic, json.dumps(payload))

    def deploy_application(self, app_config: Dict[str, Any]) -> bool:
        try:
            deployment_type = app_config.get("type", "docker")
            app_name = app_config.get("name", "unknown")
            logger.info("Deploying application %s (type=%s)", app_name, deployment_type)

            if deployment_type == "docker":
                return self._deploy_docker_app(app_config)
            if deployment_type == "kubernetes":
                return self._deploy_k8s_app(app_config)

            logger.error("Unsupported deployment type: %s", deployment_type)
            return False

        except Exception as exc:
            logger.error("Error deploying application: %s", exc)
            return False

    def _deploy_docker_app(self, app_config: Dict[str, Any]) -> bool:
        if not self.docker_handler:
            logger.error("Docker handler not initialized")
            return False

        try:
            container_id = self.docker_handler.deploy_container(app_config)
            if not container_id:
                logger.error("Failed to deploy Docker application")
                return False

            logger.info("Docker application deployed: %s", container_id)
            if self.mqtt_handler:
                message = {
                    "type": "deployment",
                    "status": "success",
                    "container_id": container_id,
                    "application": app_config.get("name"),
                }
                topic = (
                    self.config.get("mqtt", {})
                    .get("topics", {})
                    .get(
                        "deployments",
                        "edge/deployments",
                    )
                )
                self.mqtt_handler.publish(topic, json.dumps(message))
            return True
        except Exception as exc:
            logger.error("Error deploying Docker application: %s", exc)
            return False

    def _deploy_k8s_app(self, app_config: Dict[str, Any]) -> bool:
        if not self.k8s_controller:
            logger.error("Kubernetes controller not initialized")
            return False

        yaml_file = app_config.get("yaml_file")
        namespace = app_config.get("namespace", "default")
        if not yaml_file:
            logger.error("No YAML file specified for Kubernetes deployment")
            return False

        try:
            success = self.k8s_controller.deploy_from_yaml(yaml_file, namespace)
            if success and self.mqtt_handler:
                message = {
                    "type": "deployment",
                    "status": "success",
                    "platform": "kubernetes",
                    "namespace": namespace,
                    "application": app_config.get("name"),
                }
                topic = (
                    self.config.get("mqtt", {})
                    .get("topics", {})
                    .get(
                        "deployments",
                        "edge/deployments",
                    )
                )
                self.mqtt_handler.publish(topic, json.dumps(message))
            return success
        except Exception as exc:
            logger.error("Error deploying Kubernetes application: %s", exc)
            return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge deployment manager agent")
    parser.add_argument(
        "--config",
        default="configs/config.yaml",
        help="Path to agent configuration file",
    )
    args = parser.parse_args()

    try:
        manager = EdgeDeploymentManager(config_path=args.config)
        manager.start()

        try:
            while True:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")

        manager.stop()

    except Exception as exc:
        logger.error("Fatal error in main: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
