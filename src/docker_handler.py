#!/usr/bin/env python3
"""
Docker Handler for Edge Deployment Manager
Handles Docker container operations for edge deployments
"""

import docker
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DockerHandler:
    """Handle Docker container operations"""

    def __init__(self):
        """Initialize Docker client"""
        try:
            self.client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except docker.errors.DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"Unexpected error initializing Docker client: {e}")
            raise

    def list_containers(self, all_containers: bool = False) -> \
            List[Dict[str, Any]]:
        """List all containers"""
        try:
            containers = self.client.containers.list(all=all_containers)
            container_list = []

            for container in containers:
                image_tag = (
                    container.image.tags[0] 
                    if container.image.tags 
                    else container.image.id
                )
                container_info = {
                    "id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "image": image_tag,
                    "created": container.attrs["Created"],
                    "ports": container.attrs["NetworkSettings"]["Ports"],
                }
                container_list.append(container_info)

            logger.info(f"Found {len(container_list)} containers")
            return container_list

        except docker.errors.DockerException as e:
            logger.error(f"Error listing containers: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing containers: {e}")
            return []

    def get_container(self, container_id: str):
        """Get container by ID or name"""
        try:
            return self.client.containers.get(container_id)
        except docker.errors.NotFound:
            logger.error(f"Container {container_id} not found")
            return None
        except docker.errors.DockerException as e:
            logger.error(f"Error getting container {container_id}: {e}")
            return None
        except Exception as e:
            error_msg = f"Unexpected error getting {container_id}: {e}"
            logger.error(error_msg)
            return None

    def deploy_container(self, config: Dict[str, Any]) -> Optional[str]:
        """Deploy a container based on configuration"""
        try:
            name = config.get('name', 'unknown')
            logger.info(f"Deploying container: {name}")

            # Extract configuration
            image = config.get('image')
            if not image:
                logger.error("No image specified in configuration")
                return None

            ports = config.get('ports', {})
            environment = config.get('environment', {})
            volumes = config.get('volumes', {})
            command = config.get('command')
            working_dir = config.get('working_dir')
            restart_policy = config.get(
                'restart_policy', 
                {'Name': 'unless-stopped'}
            )

            # Deploy container
            container = self.client.containers.run(
                image=image,
                name=config.get('name'),
                ports=ports,
                environment=environment,
                volumes=volumes,
                command=command,
                working_dir=working_dir,
                restart_policy=restart_policy,
                detach=True,
                remove=config.get('remove', False)
            )

            logger.info(f"Container {container.id} deployed successfully")
            return container.id

        except docker.errors.ImageNotFound as e:
            logger.error(f"Image not found: {e}")
            return None
        except docker.errors.ContainerError as e:
            logger.error(f"Container error: {e}")
            return None
        except docker.errors.DockerException as e:
            logger.error(f"Docker error deploying container: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error deploying container: {e}")
            return None

    def stop_container(self, container_id: str) -> bool:
        """Stop a container"""
        try:
            container = self.get_container(container_id)
            if container:
                container.stop()
                logger.info(f"Container {container_id} stopped")
                return True
            return False
        except docker.errors.DockerException as e:
            logger.error(f"Error stopping container {container_id}: {e}")
            return False
        except Exception as e:
            error_msg = f"Error stopping container {container_id}: {e}"
            logger.error(error_msg)
            return False

    def remove_container(self, container_id: str) -> bool:
        """Remove a container"""
        try:
            container = self.get_container(container_id)
            if container:
                container.remove(force=True)
                logger.info(f"Container {container_id} removed")
                return True
            return False
        except docker.errors.DockerException as e:
            logger.error(f"Error removing container {container_id}: {e}")
            return False
        except Exception as e:
            error_msg = f"Error removing container {container_id}: {e}"
            logger.error(error_msg)
            return False

    def get_container_logs(self, container_id: str) -> str:
        """Get container logs"""
        try:
            container = self.get_container(container_id)
            if container:
                return container.logs().decode('utf-8')
            return ""
        except docker.errors.DockerException as e:
            error_msg = f"Error getting logs for container {container_id}: {e}"
            logger.error(error_msg)
            return ""

    def get_container_stats(self, container_id: str) -> \
            Optional[Dict[str, Any]]:
        """Get container resource usage statistics"""
        try:
            container = self.get_container(container_id)
            if not container:
                return None

            stats = container.stats(stream=False)
            cpu_stats = stats.get("cpu_stats", {})
            memory_stats = stats.get("memory_stats", {})

            networks = stats.get("networks", {})
            eth0_stats = networks.get("eth0", {})

            return {
                "cpu_usage": cpu_stats.get("cpu_usage", {}).get(
                    "total_usage", 0),
                "memory_usage": memory_stats.get("usage", 0),
                "memory_limit": memory_stats.get("limit", 0),
                "network_rx": eth0_stats.get("rx_bytes", 0),
                "network_tx": eth0_stats.get("tx_bytes", 0),
                "timestamp": stats.get("read", "")
            }

        except docker.errors.DockerException as e:
            error_msg = (
                f"Unexpected error getting stats for "
                f"{container_id}: {e}"
            )
            logger.error(error_msg)
            return None
        except Exception as e:
            error_msg = f"Unexpected error getting stats for container {container_id}: {e}"
            logger.error(error_msg)
            return None

    def pull_image(self, image: str) -> bool:
        """Pull an image from registry"""
        try:
            self.client.images.pull(image)
            logger.info(f"Image {image} pulled successfully")
            return True
        except docker.errors.DockerException as e:
            logger.error(f"Error pulling image {image}: {e}")
            return False

    def build_image(self, path: str, tag: str, 
                   dockerfile: str = "Dockerfile") -> Optional[str]:
        """Build an image from Dockerfile"""
        try:
            logger.info(f"Building image {tag} from {path}")
            image, logs = self.client.images.build(
                path=path, tag=tag, dockerfile=dockerfile, decode=True
            )

            # Log build output
            for log in logs:
                if 'stream' in log:
                    logger.info(log['stream'].strip())

            logger.info(f"Image {tag} built successfully")
            return image.id

        except docker.errors.BuildError as e:
            logger.error(f"Error building image {tag}: {e}")
            return None
        except docker.errors.DockerException as e:
            logger.error(f"Docker error building image {tag}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error building image {tag}: {e}")
            return None
