"""
Edge Deployment Manager
=======================

A comprehensive edge deployment management system with support for:
- Docker container deployment
- Kubernetes orchestration
- MQTT communication
- IoT edge device management

Main Components:
- EdgeDeploymentManager: Main orchestration class
- DockerHandler: Docker container management
- KubernetesController: Kubernetes cluster management
- MQTTHandler: MQTT communication for IoT devices
"""

__version__ = "1.0.0"
__author__ = "Edge Deployment Manager Team"

# Import main classes for easier access
from .manager import EdgeDeploymentManager
from .docker_handler import DockerHandler
from .k8s_controller import KubernetesController
from .mqtt_handler import MQTTHandler

__all__ = [
    "EdgeDeploymentManager",
    "DockerHandler",
    "KubernetesController",
    "MQTTHandler",
]
