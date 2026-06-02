# edge-stack Helm chart

Deploys the full edge stack:

- PostgreSQL (device registry)
- Mosquitto (mTLS MQTT)
- Control plane (HA, 2 replicas by default)
- Edge agent (Docker socket optional)

## Prerequisites

1. Build and load the application image (or push to your registry):

```bash
docker build -t edge-deployment-manager:latest .
```

2. Create Kubernetes secrets **before** install:

| Secret | Keys |
|--------|------|
| `edge-control-plane-secrets` | `CONTROL_PLANE_API_TOKEN`, `EDGE_COMMAND_SIGNING_KEY_HEX`, `EDGE_BOOTSTRAP_TOKEN` |
| `edge-mqtt-tls` | `ca.crt`, `mqtt-server.crt`, `mqtt-server.key`, `control-plane-mqtt.crt`, `control-plane-mqtt.key` |
| `edge-agent-credentials` | `ca.crt`, `agent.crt`, `agent.key` |

Generate PKI locally with `make setup-dev` and copy PEM files from `certs/` and `runtime/agent-credentials/`.

3. Set `edgeAgent.signingPublicKeyHex` in `values.yaml` (from setup output).

## Install

```bash
helm upgrade --install edge-stack ./deploy/helm/edge-stack \
  --set controlPlane.existingSecret=edge-control-plane-secrets \
  --set mosquitto.tls.existingSecret=edge-mqtt-tls \
  --set edgeAgent.credentialsSecret=edge-agent-credentials \
  --set edgeAgent.signingPublicKeyHex="<hex>"
```

## Verify

```bash
kubectl port-forward svc/edge-stack-control-plane 8080:8080
curl -sk -H "Authorization: Bearer $TOKEN" https://127.0.0.1:8080/v1/leader
```

## Notes

- Bootstrap enroll is typically run **once** against a control plane Pod to create agent credentials, then store them in `edge-agent-credentials`.
- For production, use cert-manager or your secret manager instead of long-lived bootstrap tokens.
- Enable `edgeAgent.redis.url` when running multiple agent replicas with shared replay protection.
