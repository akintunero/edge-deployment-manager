import yaml
import paho.mqtt.client as mqtt

# Load configuration
with open("configs/config.yaml", "r") as file:
    config = yaml.safe_load(file)

print(f"Edge Deployment Manager initialized with config: {config}")
