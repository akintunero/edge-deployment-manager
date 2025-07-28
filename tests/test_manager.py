#!/usr/bin/env python3
"""
Unit tests for Edge Deployment Manager
"""

import unittest
import tempfile
import os
import yaml
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the modules to test
import sys
import os

# Add project root and src to path for compatibility
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)

# Import the classes - try multiple import paths for flexibility
try:
    # Try importing from installed package
    from src.manager import EdgeDeploymentManager
    from src.mqtt_handler import MQTTHandler
    from src.docker_handler import DockerHandler
    from src.k8s_controller import KubernetesController
except ImportError:
    try:
        # Fallback: try direct import from src module
        import src.manager as manager_module
        import src.mqtt_handler as mqtt_module
        import src.docker_handler as docker_module
        import src.k8s_controller as k8s_module
        
        EdgeDeploymentManager = manager_module.EdgeDeploymentManager
        MQTTHandler = mqtt_module.MQTTHandler
        DockerHandler = docker_module.DockerHandler
        KubernetesController = k8s_module.KubernetesController
    except ImportError:
        # Final fallback: direct import from current working directory
        from manager import EdgeDeploymentManager
        from mqtt_handler import MQTTHandler
        from docker_handler import DockerHandler
        from k8s_controller import KubernetesController


class TestEdgeDeploymentManager(unittest.TestCase):
    """Test cases for EdgeDeploymentManager"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yaml")
        
        # Create test configuration
        test_config = {
            'mqtt': {
                'broker': 'localhost',
                'port': 1883,
                'keepalive': 60
            },
            'docker': {
                'socket': '/var/run/docker.sock'
            },
            'kubernetes': {
                'namespace': 'default'
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('src.manager.MQTTHandler')
    @patch('src.manager.DockerHandler')
    @patch('src.manager.KubernetesController')
    def test_manager_initialization(self, mock_k8s, mock_docker, mock_mqtt):
        """Test manager initialization"""
        # Mock the handlers to avoid actual connections
        mock_mqtt.return_value = Mock()
        mock_docker.return_value = Mock()
        mock_k8s.return_value = Mock()
        
        manager = EdgeDeploymentManager(self.config_file)
        
        self.assertIsNotNone(manager.config)
        self.assertIn('mqtt', manager.config)
        self.assertIn('docker', manager.config)
        self.assertIn('kubernetes', manager.config)

    def test_config_loading(self):
        """Test configuration loading"""
        manager = EdgeDeploymentManager(self.config_file)
        
        # Test that config is loaded correctly
        self.assertEqual(manager.config['mqtt']['broker'], 'localhost')
        self.assertEqual(manager.config['mqtt']['port'], 1883)

    def test_config_file_not_found(self):
        """Test error handling for missing config file"""
        with self.assertRaises(FileNotFoundError):
            EdgeDeploymentManager("nonexistent_config.yaml")

    @patch('src.manager.MQTTHandler')
    @patch('src.manager.DockerHandler')
    @patch('src.manager.KubernetesController')
    def test_service_initialization(self, mock_k8s, mock_docker, mock_mqtt):
        """Test service initialization"""
        # Mock the handlers
        mock_mqtt.return_value = Mock()
        mock_docker.return_value = Mock()
        mock_k8s.return_value = Mock()
        
        manager = EdgeDeploymentManager(self.config_file)
        manager.initialize_services()
        
        # Verify handlers were created
        self.assertIsNotNone(manager.mqtt_handler)
        self.assertIsNotNone(manager.docker_handler)
        self.assertIsNotNone(manager.k8s_controller)


class TestMQTTHandler(unittest.TestCase):
    """Test cases for MQTTHandler"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'broker': 'localhost',
            'port': 1883,
            'keepalive': 60,
            'client_id': 'test-client'
        }

    @patch('src.mqtt_handler.mqtt.Client')
    def test_mqtt_handler_initialization(self, mock_client):
        """Test MQTT handler initialization"""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        
        handler = MQTTHandler(self.config)
        
        self.assertEqual(handler.broker, 'localhost')
        self.assertEqual(handler.port, 1883)
        self.assertEqual(handler.client_id, 'test-client')

    @patch('src.mqtt_handler.mqtt.Client')
    def test_mqtt_connection(self, mock_client):
        """Test MQTT connection"""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        
        handler = MQTTHandler(self.config)
        
        # Test connection
        result = handler.start()
        # Should return False since we can't actually connect in tests
        self.assertFalse(result)


class TestDockerHandler(unittest.TestCase):
    """Test cases for DockerHandler"""

    @patch('src.docker_handler.docker.from_env')
    def test_docker_handler_initialization(self, mock_docker):
        """Test Docker handler initialization"""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        mock_client.ping.return_value = True
        
        handler = DockerHandler()
        
        self.assertIsNotNone(handler.client)

    @patch('src.docker_handler.docker.from_env')
    def test_list_containers(self, mock_docker):
        """Test listing containers"""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        # Mock container list
        mock_container = Mock()
        mock_container.id = "test-container-id"
        mock_container.name = "test-container"
        mock_container.status = "running"
        mock_container.image.tags = ["test-image:latest"]
        mock_container.attrs = {
            'Created': '2023-01-01T00:00:00Z',
            'NetworkSettings': {'Ports': {}}
        }
        
        mock_client.containers.list.return_value = [mock_container]
        
        handler = DockerHandler()
        containers = handler.list_containers()
        
        self.assertEqual(len(containers), 1)
        self.assertEqual(containers[0]['name'], 'test-container')


class TestKubernetesController(unittest.TestCase):
    """Test cases for KubernetesController"""

    @patch('src.k8s_controller.config.load_kube_config')
    @patch('src.k8s_controller.client.CoreV1Api')
    @patch('src.k8s_controller.client.AppsV1Api')
    @patch('src.k8s_controller.client.NetworkingV1Api')
    def test_k8s_controller_initialization(self, mock_networking, mock_apps, mock_core, mock_config):
        """Test Kubernetes controller initialization"""
        # Mock the API clients
        mock_core_instance = Mock()
        mock_core.return_value = mock_core_instance
        mock_core_instance.list_namespace.return_value = Mock()
        
        mock_apps_instance = Mock()
        mock_apps.return_value = mock_apps_instance
        
        mock_networking_instance = Mock()
        mock_networking.return_value = mock_networking_instance
        
        controller = KubernetesController()
        
        self.assertIsNotNone(controller.core_v1)
        self.assertIsNotNone(controller.apps_v1)
        self.assertIsNotNone(controller.networking_v1)

    @patch('src.k8s_controller.config.load_kube_config')
    @patch('src.k8s_controller.client.CoreV1Api')
    @patch('src.k8s_controller.client.AppsV1Api')
    @patch('src.k8s_controller.client.NetworkingV1Api')
    def test_list_namespaces(self, mock_networking, mock_apps, mock_core, mock_config):
        """Test listing namespaces"""
        # Mock the API clients
        mock_core_instance = Mock()
        mock_core.return_value = mock_core_instance
        
        # Mock namespace list
        mock_namespace = Mock()
        mock_namespace.metadata.name = "test-namespace"
        mock_namespace.status.phase = "Active"
        mock_namespace.metadata.creation_timestamp = None
        
        mock_namespace_list = Mock()
        mock_namespace_list.items = [mock_namespace]
        mock_core_instance.list_namespace.return_value = mock_namespace_list
        
        controller = KubernetesController()
        namespaces = controller.list_namespaces()
        
        self.assertEqual(len(namespaces), 1)
        self.assertEqual(namespaces[0]['name'], 'test-namespace')


if __name__ == "__main__":
    unittest.main()
