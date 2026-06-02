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

__version__ = "2.0.0"
__author__ = "Olúmáyòwá Akinkuehinmi"

from .docker_handler import DockerHandler
from .k8s_controller import KubernetesController

# Import main classes for easier access
from .manager import EdgeDeploymentManager
from .mqtt_handler import MQTTHandler

__all__ = [
    "EdgeDeploymentManager",
    "DockerHandler",
    "KubernetesController",
    "MQTTHandler",
]
