from kubernetes import client, config

config.load_kube_config()
api = client.CoreV1Api()  #
print("Connected to Kubernetes cluster")
