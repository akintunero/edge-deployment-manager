from kubernetes import client, config

config.load_kube_config()
print("Connected to Kubernetes cluster")
