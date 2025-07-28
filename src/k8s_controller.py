#!/usr/bin/env python3
"""
Kubernetes Controller for Edge Deployment Manager
Handles Kubernetes deployment operations for edge clusters
"""

from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class KubernetesController:
    """Handles Kubernetes deployment operations for edge clusters"""

    def __init__(self, config_file: Optional[str] = None):
        try:
            # Load Kubernetes configuration
            if config_file:
                config.load_kube_config(config_file)
            else:
                config.load_kube_config()

            # Initialize API clients
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.networking_v1 = client.NetworkingV1Api()

            # Test connection
            self.core_v1.list_namespace()
            logger.info("Kubernetes client initialized successfully")

        except config.ConfigException as e:
            logger.error(f"Failed to load Kubernetes configuration: {e}")
            raise
        except ApiException as e:
            logger.error(f"Failed to connect to Kubernetes cluster: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing Kubernetes client: {e}")
            raise

    def list_namespaces(self) -> List[Dict[str, Any]]:
        """List all namespaces"""
        try:
            namespaces = self.core_v1.list_namespace()
            namespace_list = []

            for namespace in namespaces.items:
                namespace_info = {
                    "name": namespace.metadata.name,
                    "status": namespace.status.phase,
                    "created": (
                        namespace.metadata.creation_timestamp.isoformat()
                        if namespace.metadata.creation_timestamp
                        else None
                    ),
                }
                namespace_list.append(namespace_info)

            logger.info(f"Found {len(namespace_list)} namespaces")
            return namespace_list

        except ApiException as e:
            logger.error(f"Error listing namespaces: {e}")
            return []

    def list_pods(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """List pods in a namespace"""
        try:
            pods = self.core_v1.list_namespaced_pod(namespace)
            pod_list = []

            for pod in pods.items:
                pod_info = {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "ready": pod.status.ready,
                    "restarts": pod.status.container_statuses[0].restart_count if pod.status.container_statuses else 0,
                    "created": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                }
                pod_list.append(pod_info)

            logger.info(f"Found {len(pod_list)} pods in namespace {namespace}")
            return pod_list

        except ApiException as e:
            logger.error(f"Error listing pods in namespace {namespace}: {e}")
            return []

    def list_deployments(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """List deployments in a namespace"""
        try:
            deployments = self.apps_v1.list_namespaced_deployment(namespace)
            deployment_list = []

            for deployment in deployments.items:
                deployment_info = {
                    "name": deployment.metadata.name,
                    "namespace": deployment.metadata.namespace,
                    "replicas": deployment.spec.replicas,
                    "available": deployment.status.available_replicas,
                    "ready": deployment.status.ready_replicas,
                    "created": (
                        deployment.metadata.creation_timestamp.isoformat()
                        if deployment.metadata.creation_timestamp
                        else None
                    ),
                }
                deployment_list.append(deployment_info)

            logger.info(f"Found {len(deployment_list)} deployments in namespace {namespace}")
            return deployment_list

        except ApiException as e:
            logger.error(f"Error listing deployments in namespace {namespace}: {e}")
            return []

    def deploy_from_yaml(self, yaml_file: str, namespace: str = "default") -> bool:
        """Deploy resources from YAML file"""
        try:
            logger.info(f"Deploying from YAML file: {yaml_file}")

            with open(yaml_file, "r") as file:
                yaml_content = yaml.safe_load_all(file)

                for resource in yaml_content:
                    if resource is None:
                        continue

                    kind = resource.get("kind")
                    name = resource.get("metadata", {}).get("name")

                    logger.info(f"Deploying {kind}: {name}")

                    if kind == "Deployment":
                        self._create_deployment(resource, namespace)
                    elif kind == "Service":
                        self._create_service(resource, namespace)
                    elif kind == "ConfigMap":
                        self._create_configmap(resource, namespace)
                    elif kind == "Secret":
                        self._create_secret(resource, namespace)
                    else:
                        logger.warning(f"Unsupported resource kind: {kind}")

            logger.info(f"Successfully deployed resources from {yaml_file}")
            return True

        except FileNotFoundError:
            logger.error(f"YAML file not found: {yaml_file}")
            return False
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {yaml_file}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deploying from YAML file {yaml_file}: {e}")
            return False

    def _create_deployment(self, deployment_config: Dict[str, Any], namespace: str):
        """Create a deployment"""
        try:
            deployment = client.V1Deployment(
                metadata=client.V1ObjectMeta(name=deployment_config["metadata"]["name"], namespace=namespace),
                spec=deployment_config["spec"],
            )

            self.apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
            logger.info(f"Deployment created: {deployment_config['metadata']['name']}")

        except ApiException as e:
            logger.error(f"Error creating deployment: {e}")

    def _create_service(self, service_config: Dict[str, Any], namespace: str):
        """Create a service"""
        try:
            service = client.V1Service(
                metadata=client.V1ObjectMeta(name=service_config["metadata"]["name"], namespace=namespace),
                spec=service_config["spec"],
            )

            self.core_v1.create_namespaced_service(namespace=namespace, body=service)
            logger.info(f"Service created: {service_config['metadata']['name']}")

        except ApiException as e:
            logger.error(f"Error creating service: {e}")

    def _create_configmap(self, configmap_config: Dict[str, Any], namespace: str):
        """Create a configmap"""
        try:
            configmap = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=configmap_config["metadata"]["name"], namespace=namespace),
                data=configmap_config.get("data", {}),
            )

            self.core_v1.create_namespaced_config_map(namespace=namespace, body=configmap)
            logger.info(f"ConfigMap created: {configmap_config['metadata']['name']}")

        except ApiException as e:
            logger.error(f"Error creating configmap: {e}")

    def _create_secret(self, secret_config: Dict[str, Any], namespace: str):
        """Create a secret"""
        try:
            secret = client.V1Secret(
                metadata=client.V1ObjectMeta(name=secret_config["metadata"]["name"], namespace=namespace),
                data=secret_config.get("data", {}),
                type=secret_config.get("type", "Opaque"),
            )

            self.core_v1.create_namespaced_secret(namespace=namespace, body=secret)
            logger.info(f"Secret created: {secret_config['metadata']['name']}")

        except ApiException as e:
            logger.error(f"Error creating secret: {e}")

    def scale_deployment(self, name: str, replicas: int, namespace: str = "default") -> bool:
        """Scale a deployment"""
        try:
            logger.info(f"Scaling deployment {name} to {replicas} replicas")

            self.apps_v1.patch_namespaced_deployment_scale(
                name=name, namespace=namespace, body={"spec": {"replicas": replicas}}
            )

            logger.info(f"Successfully scaled deployment {name} to {replicas} replicas")
            return True

        except ApiException as e:
            logger.error(f"Error scaling deployment {name}: {e}")
            return False

    def delete_deployment(self, name: str, namespace: str = "default") -> bool:
        """Delete a deployment"""
        try:
            logger.info(f"Deleting deployment: {name}")

            self.apps_v1.delete_namespaced_deployment(name=name, namespace=namespace)

            logger.info(f"Successfully deleted deployment: {name}")
            return True

        except ApiException as e:
            logger.error(f"Error deleting deployment {name}: {e}")
            return False

    def get_pod_logs(self, pod_name: str, namespace: str = "default", tail_lines: int = 100) -> str:
        """Get pod logs"""
        try:
            logs = self.core_v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=tail_lines)
            return logs
        except ApiException as e:
            logger.error(f"Error getting logs for pod {pod_name}: {e}")
            return ""

    def get_cluster_info(self) -> Dict[str, Any]:
        """Get cluster information"""
        try:
            version = self.core_v1.get_api_resources()
            nodes = self.core_v1.list_node()

            cluster_info = {
                "timestamp": datetime.now().isoformat(),
                "node_count": len(nodes.items),
                "api_resources": len(version.resources) if version.resources else 0,
            }

            return cluster_info

        except ApiException as e:
            logger.error(f"Error getting cluster info: {e}")
            return {}

    def health_check(self) -> bool:
        """Perform health check on Kubernetes cluster"""
        try:
            self.core_v1.list_namespace()
            logger.debug("Kubernetes cluster health check passed")
            return True
        except Exception as e:
            logger.error(f"Kubernetes cluster health check failed: {e}")
            return False
