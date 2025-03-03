import yaml
import paho.mqtt.client as mqtt

# Load configuration
with open("configs/config.yaml", "r") as file:
    config = yaml.safe_load(file)

print(f"Edge Deployment Manager initialized with config: {config}")

# Initialize MQTT Client
mqtt_client = mqtt.Client()
mqtt_client.connect(config.get("mqtt_broker", "localhost"), 1883, 60)
print("MQTT client initialized and connected")
