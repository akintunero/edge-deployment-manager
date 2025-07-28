#!/usr/bin/env python3
"""
Basic Deployment Example
Demonstrates how to use the Edge Deployment Manager for simple deployments
"""

import sys
import os
import yaml
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from manager import EdgeDeploymentManager
from docker_handler import DockerHandler
from k8s_controller import KubernetesController


def basic_docker_deployment():
    """Example: Deploy a simple Docker container"""
    print("🐳 Basic Docker Deployment Example")
    print("=" * 40)
    
    try:
        # Initialize Docker handler
        docker_handler = DockerHandler()
        
        # Container configuration
        container_config = {
            'image': 'nginx:latest',
            'name': 'web-server-example',
            'ports': {'80/tcp': 8080},
            'environment': {'ENV': 'production'},
            'restart_policy': 'unless-stopped'
        }
        
        print(f"Deploying container: {container_config['name']}")
        
        # Deploy the container
        container_id = docker_handler.deploy_container(container_config)
        
        if container_id:
            print(f"✅ Container deployed successfully: {container_id}")
            
            # Get container information
            containers = docker_handler.list_containers()
            for container in containers:
                if container['name'] == container_config['name']:
                    print(f"📊 Container Status: {container['status']}")
                    print(f"🖼️  Image: {container['image']}")
                    break
        else:
            print("❌ Failed to deploy container")
            
    except Exception as e:
        print(f"❌ Error during Docker deployment: {e}")


def basic_kubernetes_deployment():
    """Example: Deploy to Kubernetes cluster"""
    print("\n☸️  Basic Kubernetes Deployment Example")
    print("=" * 40)
    
    try:
        # Initialize Kubernetes controller
        k8s_controller = KubernetesController()
        
        # Check cluster connection
        if k8s_controller.health_check():
            print("✅ Connected to Kubernetes cluster")
            
            # List namespaces
            namespaces = k8s_controller.list_namespaces()
            print(f"📁 Found {len(namespaces)} namespaces")
            
            # List deployments in default namespace
            deployments = k8s_controller.list_deployments('default')
            print(f"🚀 Found {len(deployments)} deployments in default namespace")
            
        else:
            print("❌ Failed to connect to Kubernetes cluster")
            
    except Exception as e:
        print(f"❌ Error during Kubernetes deployment: {e}")


def basic_mqtt_communication():
    """Example: MQTT communication setup"""
    print("\n📡 Basic MQTT Communication Example")
    print("=" * 40)
    
    try:
        # MQTT configuration
        mqtt_config = {
            'broker': 'localhost',
            'port': 1883,
            'keepalive': 60,
            'client_id': 'example-client'
        }
        
        from mqtt_handler import MQTTHandler
        
        # Initialize MQTT handler
        mqtt_handler = MQTTHandler(mqtt_config)
        
        # Define message handler
        def handle_deployment_message(message):
            print(f"📨 Received deployment message: {message}")
        
        # Register message handler
        mqtt_handler.register_handler('edge/deployments', handle_deployment_message)
        
        print("✅ MQTT handler initialized")
        print("📡 Ready to receive deployment messages")
        
        # Note: In a real application, you would start the MQTT client
        # mqtt_handler.start()
        
    except Exception as e:
        print(f"❌ Error during MQTT setup: {e}")


def full_deployment_example():
    """Example: Complete deployment workflow"""
    print("\n🚀 Complete Deployment Workflow Example")
    print("=" * 40)
    
    try:
        # Initialize the main manager
        manager = EdgeDeploymentManager()
        
        print("✅ Edge Deployment Manager initialized")
        print(f"📋 Configuration loaded: {manager.config}")
        
        # Initialize services
        manager.initialize_services()
        
        print("✅ All services initialized")
        print("🎯 Ready for deployment operations")
        
    except Exception as e:
        print(f"❌ Error during full deployment setup: {e}")


def main():
    """Run all basic deployment examples"""
    print("🎯 Edge Deployment Manager - Basic Examples")
    print("=" * 50)
    
    # Run examples
    basic_docker_deployment()
    basic_kubernetes_deployment()
    basic_mqtt_communication()
    full_deployment_example()
    
    print("\n✅ All examples completed!")
    print("\n📚 For more examples, see the documentation:")
    print("   https://github.com/akintunero/edge-deployment-manager")


if __name__ == "__main__":
    main() 