import paho.mqtt.client as mqtt


class MQTTHandler:

    def __init__(self):
        self.client = mqtt.Client()
