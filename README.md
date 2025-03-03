# **Edge Computing Deployment Manager**  

A lightweight and scalable **DevOps tool** designed to simplify the deployment and management of applications across **edge devices** using **Docker, Kubernetes, and MQTT**. This project enables seamless **remote orchestration**, **configuration management**, and **real-time monitoring** for IoT and distributed computing environments.  

---

##  Features
- **Edge-Optimized Deployment** – Deploy and manage applications across multiple edge devices with minimal overhead.  
- **Containerized Workloads** – Utilize **Docker** to package and deploy applications efficiently.  
- **Kubernetes Integration** – Supports **Kubernetes-based orchestration** for large-scale edge networks.  
- **MQTT Messaging** – Uses **MQTT protocol** for real-time communication and device synchronization.  
- **Lightweight & Scalable** – Built to operate efficiently on resource-constrained edge environments.  
- **CI/CD Support** – Automated testing, linting, and deployment workflows via **GitHub Actions**.  
- **Configuration Management** – YAML-based configurations for easy customization.  

---

##  Installation 

1. **Clone the Repository**  
```bash
git clone https://github.com/akintunero/edge-deployment-manager.git
cd edge-deployment-manager
```

2. **Set Up Virtual Environment**  
```bash
python3 -m venv venv
source venv/bin/activate # On macOs / Linux
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. **Install Dependencies**  
```bash
pip install -r requirements.txt
```

---

## Usage  

1. **Start the Deployment Manager**  
```bash
python src/manager.py
```
This initializes the deployment system, loads configurations, and connects to the MQTT broker.  

2. **Run Docker Containers**  
```bash
docker-compose up -d
```
This spins up edge applications in **containers**.  

3. **Deploy an Application via Kubernetes**  
```bash
kubectl apply -f configs/deployment.yaml
```
Deploy applications to an **edge Kubernetes cluster**.  

3. **Monitor MQTT Messages**  
```bash
mosquitto_sub -h localhost -t "edge/deployments"
```
Subscribe to real-time **deployment events and logs**.  

---

##  Project Structure 
```
edge-deployment-manager/
│── configs/                # Configuration files (YAML)
│── docs/                   # Documentation
│── src/
│   ├── __init__.py
│   ├── manager.py          # Main deployment manager
│   ├── mqtt_handler.py     # Handles MQTT messaging
│   ├── docker_handler.py   # Docker integration
│   ├── k8s_controller.py   # Kubernetes deployment
│── tests/                  # Unit tests
│── .github/workflows/      # CI/CD pipelines
│── requirements.txt        # Dependencies
│── README.md               # Project documentation
│── Dockerfile              # Container setup
│── LICENSE                 # Open-source license
```

---

##  Running Tests 
Run unit tests to validate functionality:  
```bash
pytest tests/
```

---

## Contributing

 **Contributions are welcome!** If you'd like to improve this project. 




## License 
This project is licensed under the **MIT License**.
