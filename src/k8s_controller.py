#!/usr/bin/env python3
"""
Kubernetes Controller for Edge Deployment Manager
Handles Kubernetes deployment operations for edge clusters
"""

import yaml
import logging
from typing import Dict, List, Any
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class KubernetesController:
    """Handle Kubernetes cluster operations"""

    def __init__(self):
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

            # Initialize API clients
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.networking_v1 = client.NetworkingV1Api()

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
                restarts = (
                    container_statuses[0].restart_count 
                    if container_statuses else 0
                )
                
                # Handle creation timestamp safely
                creation_time = (
                    pod.metadata.creation_timestamp.isoformat() 
                    if pod.metadata.creation_timestamp else None
                )

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

    def list_deployments(self, namespace: str = "default") -> \
            List[Dict[str, Any]]:
        """List deployments in a namespace"""
        try:
            deployments = self.apps_v1.list_namespaced_deployment(
                namespace=namespace)
            deployment_list = []

            for deployment in deployments.items:
                deployment_info = {
                    "name": deployment.metadata.name,
                    "namespace": deployment.metadata.namespace,
                    "replicas": deployment.spec.replicas,
                    "ready_replicas": (deployment.status.ready_replicas
                                     or 0),
                    "available_replicas": (deployment.status.available_replicas
                                         or 0),
                    "created": (deployment.metadata.creation_timestamp.
                              isoformat()),
                }
                deployment_list.append(deployment_info)

            logger.info(
                f"Found {len(deployment_list)} deployments in "
                f"namespace {namespace}")
            return deployment_list

        except ApiException as e:
            error_msg = (f"Error listing deployments in namespace "
                        f"{namespace}: {e}")
            logger.error(error_msg)
            return []

    def deploy_from_yaml(self, yaml_file: str,
                        namespace: str = "default") -> bool:
        """Deploy resources from YAML file"""
        try:
            with open(yaml_file, 'r') as file:
                resources = yaml.safe_load_all(file)

                for resource in resources:
                    if not resource:
                        continue

                    kind = resource.get('kind')
                    metadata = resource.get('metadata', {})
                    resource_name = metadata.get('name', 'unknown')

                    logger.info(f"Deploying {kind}: {resource_name}")

                    if kind == 'Deployment':
                        self._deploy_deployment(resource, namespace)
                    elif kind == 'Service':
                        self._deploy_service(resource, namespace)
                    elif kind == 'ConfigMap':
                        self._deploy_configmap(resource, namespace)
                    elif kind == 'Secret':
                        self._deploy_secret(resource, namespace)
                    else:
                        logger.warning(f"Unsupported resource type: {kind}")

                logger.info(f"Deployed resources from {yaml_file}")
                return True

        except FileNotFoundError:
            logger.error(f"YAML file not found: {yaml_file}")
            return False
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {yaml_file}: {e}")
            return False
        except ApiException as e:
            logger.error(f"Kubernetes API error deploying {yaml_file}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deploying {yaml_file}: {e}")
            return False

    def _deploy_deployment(self, resource: Dict[str, Any],
                          namespace: str) -> None:
        """Deploy a Deployment resource"""
        try:
            # Set namespace if not specified
            if 'namespace' not in resource['metadata']:
                resource['metadata']['namespace'] = namespace

            deployment = client.V1Deployment(**resource)
            self.apps_v1.create_namespaced_deployment(
                namespace=namespace, body=deployment)

            name = resource['metadata']['name']
            logger.info(f"Deployment {name} created successfully")

        except ApiException as e:
            if e.status == 409:  # Already exists
                error_msg = f"Deployment already exists, updating: {e}"
                logger.warning(error_msg)
                self._update_deployment(resource, namespace)
            else:
                logger.error(f"Error creating deployment: {e}")
                raise

    def _deploy_service(self, resource: Dict[str, Any],
                       namespace: str) -> None:
        """Deploy a Service resource"""
        try:
            if 'namespace' not in resource['metadata']:
                resource['metadata']['namespace'] = namespace

            service = client.V1Service(**resource)
            self.core_v1.create_namespaced_service(
                namespace=namespace, body=service)

            name = resource['metadata']['name']
            logger.info(f"Service {name} created successfully")

        except ApiException as e:
            if e.status == 409:
                error_msg = f"Service already exists: {e}"
                logger.warning(error_msg)
            else:
                logger.error(f"Error creating service: {e}")
                raise

    def _deploy_configmap(self, resource: Dict[str, Any],
                         namespace: str) -> None:
        """Deploy a ConfigMap resource"""
        try:
            if 'namespace' not in resource['metadata']:
                resource['metadata']['namespace'] = namespace

            configmap = client.V1ConfigMap(**resource)
            self.core_v1.create_namespaced_config_map(
                namespace=namespace, body=configmap)

            name = resource['metadata']['name']
            logger.info(f"ConfigMap {name} created successfully")

        except ApiException as e:
            if e.status == 409:
                error_msg = f"ConfigMap already exists: {e}"
                logger.warning(error_msg)
            else:
                logger.error(f"Error creating configmap: {e}")
                raise

    def _deploy_secret(self, resource: Dict[str, Any],
                      namespace: str) -> None:
        """Deploy a Secret resource"""
        try:
            if 'namespace' not in resource['metadata']:
                resource['metadata']['namespace'] = namespace

            secret = client.V1Secret(**resource)
            self.core_v1.create_namespaced_secret(
                namespace=namespace, body=secret)

            name = resource['metadata']['name']
            logger.info(f"Secret {name} created successfully")

        except ApiException as e:
            if e.status == 409:
                error_msg = f"Secret already exists: {e}"
                logger.warning(error_msg)
            else:
                logger.error(f"Error creating secret: {e}")
                raise

    def _update_deployment(self, resource: Dict[str, Any],
                          namespace: str) -> None:
        """Update an existing deployment"""
        try:
            deployment = client.V1Deployment(**resource)
            name = resource['metadata']['name']

            self.apps_v1.patch_namespaced_deployment(
                name=name, namespace=namespace, body=deployment)

            logger.info(f"Deployment {name} updated successfully")

        except ApiException as e:
            logger.error(f"Error updating deployment: {e}")
            raise

    def scale_deployment(self, name: str, replicas: int,
                        namespace: str = "default") -> bool:
        """Scale a deployment"""
        try:
            # Create scale object
            scale = client.V1Scale(
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                spec=client.V1ScaleSpec(replicas=replicas)
            )

            # Scale the deployment
            self.apps_v1.patch_namespaced_deployment_scale(
                name=name, namespace=namespace, body=scale)

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

    def delete_deployment(self, name: str,
                         namespace: str = "default") -> bool:
        """Delete a deployment"""
        try:
            self.apps_v1.delete_namespaced_deployment(
                name=name, namespace=namespace)

            logger.info(f"Deployment {name} deleted successfully")
            return True

        except ApiException as e:
            logger.error(f"Error deleting deployment {name}: {e}")
            return False
        except Exception as e:
            error_msg = f"Unexpected error deleting deployment {name}: {e}"
            logger.error(error_msg)
            return False

    def get_pod_logs(self, pod_name: str, namespace: str = "default",
                    container: str = None) -> str:
        """Get logs from a pod"""
        try:
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container
            )
            return logs

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
