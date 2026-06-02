# Production Quickstart (Local Stack)

One-command local stack with mTLS MQTT, HTTPS control plane, agent enrollment, and a
sample signed deploy command.

## Prerequisites

- Docker and Docker Compose
- Python 3.10+

## Start the stack

```bash
make prod-up
```

This will:

1. Generate PKI assets, signing keys, and `.env` (`make setup-dev`)
2. Start Mosquitto (mTLS on `8883`) and control plane (`https://localhost:8080`)
3. Bootstrap-enroll `edge-agent-001` and write credentials to `runtime/agent-credentials/`
4. Start the edge agent with Docker socket access

## Verify health

```bash
curl -sk https://localhost:8080/health
curl -sk https://localhost:8080/ready
curl -sk https://localhost:8080/metrics
curl -s http://localhost:9090/health
curl -s http://localhost:9090/ready
curl -s http://localhost:9090/metrics
```

## Issue a deploy command

```bash
make prod-deploy-example
```

This publishes a signed `deploy` command for `nginx:alpine` mapped to host port `8088`.

Verify:

```bash
docker ps --filter name=nginx-edge-demo
curl -s http://localhost:8088
```

## Stop the stack

```bash
make prod-down
```

## Observability

- Control plane logs: JSON to stdout (`logging.json: true`)
- Agent metrics: `http://localhost:9090/metrics`
- Useful metrics: `edge_mqtt_connected`, `edge_commands_accepted_total`, `control_plane_commands_published_total`

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Agent not ready | `curl -s http://localhost:9090/ready` — MQTT must be connected |
| Enroll fails | Control plane healthy? `EDGE_BOOTSTRAP_TOKEN` in `.env`? |
| Deploy rejected | Image must match policy (`nginx:*`) |
| MQTT TLS errors | Re-run `make setup-dev` and `make prod-up` |
