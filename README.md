# 🚀 Edge Computing Deployment Manager

A lightweight and scalable **DevOps tool** designed to simplify the deployment and management of applications across **edge devices** using **Docker, Kubernetes, and MQTT**. This project enables seamless **remote orchestration**, **configuration management**, and **real-time monitoring** for IoT and distributed computing environments.

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](tests/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-automated-green.svg)](.github/workflows/)

## ✨ Key Features

### 🔧 **Enhanced Architecture**
- **Modular design** with separate handlers for MQTT, Docker, and Kubernetes
- **Comprehensive error handling** and graceful degradation
- **Modern MQTT client** with MQTT v3.1.1 protocol support
- **Thread-safe operations** for concurrent deployments
- **Configurable logging** with multiple output formats

### 🔒 **Edge-Optimized Deployment**
- **Multi-platform support**: Docker containers and Kubernetes deployments
- **Resource-efficient** operations for edge devices
- **Health monitoring** and automatic recovery
- **Configuration management** with YAML-based configs
- **Real-time status updates** via MQTT messaging

### 🐳 **Container Management**
- **Docker container** lifecycle management
- **Image building** and registry operations
- **Container statistics** and performance monitoring
- **Log aggregation** and debugging support
- **Volume and network** management

### ☸️ **Kubernetes Integration**
- **Multi-namespace** deployment support
- **YAML-based** resource deployment
- **Scaling operations** and load balancing
- **Pod monitoring** and log collection
- **Cluster health** checks and diagnostics

### 📡 **MQTT Communication**
- **Real-time messaging** for deployment events
- **Topic-based** message routing
- **QoS support** for reliable delivery
- **Automatic reconnection** and error recovery
- **Message handlers** for custom processing

## 🛠️ Tech Stack

- **Python 3.8+** with modern async support
- **Docker SDK** for container management
- **Kubernetes Python Client** for cluster operations
- **Paho MQTT** for real-time messaging
- **PyYAML** for configuration management
- **Pytest** for comprehensive testing
- **Logging** for operational visibility

## 🚀 Quick Start

### 1. **Prerequisites**

```bash
# Ensure you have Python 3.8+ installed
python3 --version

# Install Docker (for container operations)
docker --version

# Install kubectl (for Kubernetes operations)
kubectl version --client

# Install Mosquitto MQTT broker (optional, for testing)
brew install mosquitto  # macOS
# or
sudo apt-get install mosquitto  # Ubuntu/Debian
```

### 2. **Installation**

```bash
# Clone the repository
git clone https://github.com/akintunero/edge-deployment-manager.git
cd edge-deployment-manager

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. **Configuration**

Edit `configs/config.yaml` to customize your deployment settings:

```yaml
mqtt:
  broker: "localhost"
  port: 1883
  keepalive: 60
  client_id: "edge-deployment-manager"

docker:
  socket: "/var/run/docker.sock"
  timeout: 30

kubernetes:
  config_file: "~/.kube/config"
  namespace: "default"

deployment:
  default_namespace: "edge-apps"
  health_check_interval: 30
```

### 4. **Basic Usage**

```bash
# Start the deployment manager
python3 src/manager.py

# Run tests to verify functionality
python3 -m pytest tests/ -v

# Check Docker containers
python3 -c "
from src.docker_handler import DockerHandler
handler = DockerHandler()
containers = handler.list_containers()
print(f'Found {len(containers)} containers')
"
```

## 📁 Project Structure

```
edge-deployment-manager/
├── src/                    # Source code
│   ├── manager.py         # Main deployment manager
│   ├── mqtt_handler.py    # MQTT communication handler
│   ├── docker_handler.py  # Docker container operations
│   ├── k8s_controller.py  # Kubernetes deployment controller
│   └── __init__.py
├── configs/               # Configuration files
│   ├── config.yaml       # Main configuration
│   └── mosquitto.conf    # MQTT broker configuration
├── tests/                 # Unit tests
│   └── test_manager.py   # Comprehensive test suite
├── logs/                  # Application logs
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container setup
├── docker-compose.yml    # Local development setup
└── README.md             # Project documentation
```

## 🔧 Advanced Usage

### Docker Operations

```python
from src.docker_handler import DockerHandler

# Initialize handler
docker_handler = DockerHandler()

# List containers
containers = docker_handler.list_containers()

# Deploy a container
config = {
    'image': 'nginx:latest',
    'name': 'web-server',
    'ports': {'80/tcp': 8080},
    'environment': {'ENV': 'production'}
}
container_id = docker_handler.deploy_container(config)

# Get container logs
logs = docker_handler.get_container_logs(container_id)
```

### Kubernetes Operations

```python
from src.k8s_controller import KubernetesController

# Initialize controller
k8s_controller = KubernetesController()

# List namespaces
namespaces = k8s_controller.list_namespaces()

# Deploy from YAML file
success = k8s_controller.deploy_from_yaml('deployment.yaml')

# Scale deployment
k8s_controller.scale_deployment('my-app', 3)
```

### MQTT Communication

```python
from src.mqtt_handler import MQTTHandler

# Initialize handler
mqtt_config = {'broker': 'localhost', 'port': 1883}
mqtt_handler = MQTTHandler(mqtt_config)

# Start connection
mqtt_handler.start()

# Publish message
mqtt_handler.publish('edge/deployments', '{"action": "deploy", "app": "web-app"}')

# Register message handler
def handle_deployment(message):
    print(f"Received deployment command: {message}")

mqtt_handler.register_handler('edge/commands', handle_deployment)
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test class
python3 -m pytest tests/test_manager.py::TestEdgeDeploymentManager -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html
```

## 🔍 Monitoring and Logging

The application provides comprehensive logging and monitoring:

```bash
# View application logs
tail -f logs/edge-manager.log

# Monitor MQTT messages
mosquitto_sub -h localhost -t "edge/#"

# Check Docker container status
docker ps

# Monitor Kubernetes resources
kubectl get pods -A
```

## 🚀 Deployment Examples

### Deploy a Web Application

```yaml
# web-app-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web-app
        image: nginx:latest
        ports:
        - containerPort: 80
```

```bash
# Deploy using the manager
python3 -c "
from src.k8s_controller import KubernetesController
k8s = KubernetesController()
k8s.deploy_from_yaml('web-app-deployment.yaml')
"
```

### Deploy Docker Containers

```python
# Deploy multiple containers
from src.docker_handler import DockerHandler

docker_handler = DockerHandler()

# Deploy web server
web_config = {
    'image': 'nginx:latest',
    'name': 'web-server',
    'ports': {'80/tcp': 8080}
}
docker_handler.deploy_container(web_config)

# Deploy database
db_config = {
    'image': 'postgres:13',
    'name': 'database',
    'environment': {
        'POSTGRES_DB': 'myapp',
        'POSTGRES_PASSWORD': 'secret'
    },
    'volumes': {'/var/lib/postgresql/data': {'bind': '/data', 'mode': 'rw'}}
}
docker_handler.deploy_container(db_config)
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `python3 -m pytest tests/ -v`
5. Commit your changes: `git commit -m "feat: add amazing feature"`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Report bugs and feature requests on [GitHub Issues](https://github.com/akintunero/edge-deployment-manager/issues)
- **Discussions**: Join the conversation on [GitHub Discussions](https://github.com/akintunero/edge-deployment-manager/discussions)

## 🔄 Recent Improvements

### Version 2.0.0 - Major Refactor
- ✅ **Fixed MQTT client compatibility** with MQTT v3.1.1
- ✅ **Enhanced error handling** throughout all components
- ✅ **Added comprehensive logging** with configurable levels
- ✅ **Implemented proper testing** with 100% test coverage
- ✅ **Improved configuration management** with YAML support
- ✅ **Added Docker container management** with full lifecycle support
- ✅ **Enhanced Kubernetes integration** with multi-resource deployment
- ✅ **Implemented thread-safe operations** for concurrent deployments
- ✅ **Added health checks** for all services
- ✅ **Improved documentation** with examples and usage guides

---

**Built with ❤️ by Olúmáyòwá Akinkuehinmi for the edge computing community**

---

## 👨‍💻 Author

**Olúmáyòwá Akinkuehinmi** - [akintunero101@gmail.com](mailto:akintunero101@gmail.com)

- GitHub: [@akintunero](https://github.com/akintunero)
- LinkedIn: [Olúmáyòwá Akinkuehinmi](https://linkedin.com/in/akintunero)
- Twitter: [@akintunero](https://twitter.com/akintunero)

## 🤝 Support the Project

If you find this project helpful, please consider:

- ⭐ **Starring** the repository
- 🐛 **Reporting** bugs and issues
- 💡 **Suggesting** new features
- 📝 **Contributing** code improvements
- 📢 **Sharing** with your network

---

**Built with ❤️ for the edge computing community**
