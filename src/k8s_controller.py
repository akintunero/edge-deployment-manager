#!/usr/bin/env python3
"""
Kubernetes Controller for Edge Deployment Manager
Handles Kubernetes deployment operations for edge clusters
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from .k8s_manifest import apply_manifests_from_file

logger = logging.getLogger(__name__)

_SUPPORTED_MANIFEST_KINDS = ("Deployment", "Service", "ConfigMap", "Secret")


class KubernetesController:
    """Handle Kubernetes cluster operations"""

    def __init__(self) -> None:
        """Initialize Kubernetes client"""
        try:
            # Try to load configuration
            try:
                config.load_kube_config()
                logger.info("Loaded kubeconfig from default location")
            except config.ConfigException:
                logger.info("Failed to load kubeconfig, trying in-cluster")
                config.load_incluster_config()
                logger.info("Loaded in-cluster configuration")

            self._api_client = client.ApiClient()
            self.core_v1 = client.CoreV1Api(api_client=self._api_client)
            self.apps_v1 = client.AppsV1Api(api_client=self._api_client)
            self.networking_v1 = client.NetworkingV1Api(api_client=self._api_client)

            logger.info("Kubernetes client initialized successfully")

        except config.ConfigException as e:
            logger.error(f"Failed to load Kubernetes configuration: {e}")
            raise
        except ApiException as e:
            logger.error(f"Failed to connect to Kubernetes cluster: {e}")
            raise
        except Exception as e:
            error_msg = f"Unexpected error initializing Kubernetes client: {e}"
            logger.error(error_msg)
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
                    "labels": namespace.metadata.labels or {},
                }
                namespace_list.append(namespace_info)

            logger.info(f"Found {len(namespace_list)} namespaces")
            return namespace_list

        except ApiException as e:
            logger.error(f"Error listing namespaces: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing namespaces: {e}")
            return []

    def list_pods(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """List pods in a namespace"""
        try:
            pods = self.core_v1.list_namespaced_pod(namespace=namespace)
            pod_list = []

            for pod in pods.items:
                # Handle container statuses safely
                container_statuses = pod.status.container_statuses
                restarts = container_statuses[0].restart_count if container_statuses else 0

                # Handle creation timestamp safely
                creation_time = pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None

                pod_info = {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "restarts": restarts,
                    "created": creation_time,
                    "node": pod.spec.node_name or "Unknown",
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
            deployments = self.apps_v1.list_namespaced_deployment(namespace=namespace)
            deployment_list = []

            for deployment in deployments.items:
                deployment_info = {
                    "name": deployment.metadata.name,
                    "namespace": deployment.metadata.namespace,
                    "replicas": deployment.spec.replicas,
                    "ready_replicas": (deployment.status.ready_replicas or 0),
                    "available_replicas": (deployment.status.available_replicas or 0),
                    "created": (deployment.metadata.creation_timestamp.isoformat()),
                }
                deployment_list.append(deployment_info)

            logger.info(f"Found {len(deployment_list)} deployments in " f"namespace {namespace}")
            return deployment_list

        except ApiException as e:
            error_msg = f"Error listing deployments in namespace " f"{namespace}: {e}"
            logger.error(error_msg)
            return []

    def deploy_from_yaml(self, yaml_file: str, namespace: str = "default") -> bool:
        """Deploy resources from a multi-document Kubernetes manifest file."""
        return apply_manifests_from_file(
            self._api_client,
            yaml_file,
            namespace,
            allowed_kinds=_SUPPORTED_MANIFEST_KINDS,
        )

    def scale_deployment(self, name: str, replicas: int, namespace: str = "default") -> bool:
        """Scale a deployment"""
        try:
            # Create scale object
            scale = client.V1Scale(
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                spec=client.V1ScaleSpec(replicas=replicas),
            )

            # Scale the deployment
            self.apps_v1.patch_namespaced_deployment_scale(name=name, namespace=namespace, body=scale)

            logger.info(f"Deployment {name} scaled to {replicas} replicas")
            return True

        except ApiException as e:
            error_msg = f"Error scaling deployment {name}: {e}"
            logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected error scaling deployment {name}: {e}"
            logger.error(error_msg)
            return False

    def delete_deployment(self, name: str, namespace: str = "default") -> bool:
        """Delete a deployment"""
        try:
            self.apps_v1.delete_namespaced_deployment(name=name, namespace=namespace)

            logger.info(f"Deployment {name} deleted successfully")
            return True

        except ApiException as e:
            logger.error(f"Error deleting deployment {name}: {e}")
            return False
        except Exception as e:
            error_msg = f"Unexpected error deleting deployment {name}: {e}"
            logger.error(error_msg)
            return False

    def get_pod_logs(
        self,
        pod_name: str,
        namespace: str = "default",
        container: Optional[str] = None,
    ) -> str:
        """Get logs from a pod"""
        try:
            logs = self.core_v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, container=container)
            return str(logs)

        except ApiException as e:
            error_msg = f"Error getting logs for pod {pod_name}: {e}"
            logger.error(error_msg)
            return ""
        except Exception as e:
            error_msg = f"Error getting logs for pod {pod_name}: {e}"
            logger.error(error_msg)
            return ""

    def get_cluster_info(self) -> Dict[str, Any]:
        """Get cluster information"""
        try:
            version = self.core_v1.get_api_resources()
            nodes = self.core_v1.list_node()

            cluster_info = {
                "timestamp": datetime.now().isoformat(),
                "node_count": len(nodes.items),
                "api_resources": (len(version.resources) if version.resources else 0),
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
