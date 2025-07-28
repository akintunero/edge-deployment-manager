#!/usr/bin/env python3
"""
Docker Handler for Edge Deployment Manager
Handles Docker container operations for edge deployments
"""

import docker
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DockerHandler:
    """Handles Docker container operations for edge deployments"""

    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()  # Test connection
            logger.info("Docker client initialized successfully")
        except docker.errors.DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing Docker client: {e}")
            raise

    def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        """List all containers"""
        try:
            containers = self.client.containers.list(all=all_containers)
            container_list = []

            for container in containers:
                container_info = {
                    "id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else container.image.id,
                    "created": container.attrs["Created"],
                    "ports": container.attrs["NetworkSettings"]["Ports"],
                }
                container_list.append(container_info)

            logger.info(f"Found {len(container_list)} containers")
            return container_list

        except Exception as e:
            logger.error(f"Error listing containers: {e}")
            return []

    def list_images(self) -> List[Dict[str, Any]]:
        """List all Docker images"""
        try:
            images = self.client.images.list()
            image_list = []

            for image in images:
                image_info = {
                    "id": image.id,
                    "tags": image.tags,
                    "size": image.attrs["Size"],
                    "created": image.attrs["Created"],
                }
                image_list.append(image_info)

            logger.info(f"Found {len(image_list)} images")
            return image_list

        except Exception as e:
            logger.error(f"Error listing images: {e}")
            return []

    def deploy_container(self, config: Dict[str, Any]) -> Optional[str]:
        """Deploy a container based on configuration"""
        try:
            logger.info(f"Deploying container: {config.get('name', 'unknown')}")

            # Extract configuration
            image = config.get("image")
            name = config.get("name")
            ports = config.get("ports", {})
            environment = config.get("environment", {})
            volumes = config.get("volumes", {})
            restart_policy = config.get("restart_policy", "unless-stopped")

            if not image:
                logger.error("No image specified in deployment config")
                return None

            # Create container
            container = self.client.containers.run(
                image=image,
                name=name,
                ports=ports,
                environment=environment,
                volumes=volumes,
                restart_policy={"Name": restart_policy},
                detach=True,
            )

            logger.info(f"Container deployed successfully: {container.id}")
            return container.id

        except docker.errors.ImageNotFound:
            logger.error(f"Docker image not found: {config.get('image')}")
            return None
        except docker.errors.APIError as e:
            logger.error(f"Docker API error during deployment: {e}")
            return None
        except Exception as e:
            logger.error(f"Error deploying container: {e}")
            return None

    def stop_container(self, container_id: str) -> bool:
        """Stop a running container"""
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            logger.info(f"Container stopped: {container_id}")
            return True
        except docker.errors.NotFound:
            logger.error(f"Container not found: {container_id}")
            return False
        except Exception as e:
            logger.error(f"Error stopping container {container_id}: {e}")
            return False

    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a container"""
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force)
            logger.info(f"Container removed: {container_id}")
            return True
        except docker.errors.NotFound:
            logger.error(f"Container not found: {container_id}")
            return False
        except Exception as e:
            logger.error(f"Error removing container {container_id}: {e}")
            return False

    def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """Get container logs"""
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail, timestamps=True).decode("utf-8")
            return logs
        except docker.errors.NotFound:
            logger.error(f"Container not found: {container_id}")
            return ""
        except Exception as e:
            logger.error(f"Error getting logs for container {container_id}: {e}")
            return ""

    def get_container_stats(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get container statistics"""
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)

            # Extract relevant stats
            cpu_stats = stats.get("cpu_stats", {})
            memory_stats = stats.get("memory_stats", {})

            container_stats = {
                "container_id": container_id,
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": cpu_stats.get("cpu_usage", {}).get("total_usage", 0),
                "memory_usage": memory_stats.get("usage", 0),
                "memory_limit": memory_stats.get("limit", 0),
                "network_rx": stats.get("networks", {}).get("eth0", {}).get("rx_bytes", 0),
                "network_tx": stats.get("networks", {}).get("eth0", {}).get("tx_bytes", 0),
            }

            return container_stats

        except docker.errors.NotFound:
            logger.error(f"Container not found: {container_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting stats for container {container_id}: {e}")
            return None

    def pull_image(self, image_name: str, tag: str = "latest") -> bool:
        """Pull a Docker image"""
        try:
            logger.info(f"Pulling image: {image_name}:{tag}")
            self.client.images.pull(image_name, tag=tag)
            logger.info(f"Successfully pulled image: {image_name}:{tag}")
            return True
        except Exception as e:
            logger.error(f"Error pulling image {image_name}:{tag}: {e}")
            return False

    def build_image(self, path: str, tag: str, dockerfile: str = "Dockerfile") -> Optional[str]:
        """Build a Docker image"""
        try:
            logger.info(f"Building image from {path} with tag: {tag}")

            image, logs = self.client.images.build(path=path, tag=tag, dockerfile=dockerfile, decode=True)

            logger.info(f"Successfully built image: {image.id}")
            return image.id

        except Exception as e:
            logger.error(f"Error building image: {e}")
            return None

    def health_check(self) -> bool:
        """Perform health check on Docker daemon"""
        try:
            self.client.ping()
            logger.debug("Docker daemon health check passed")
            return True
        except Exception as e:
            logger.error(f"Docker daemon health check failed: {e}")
            return False
