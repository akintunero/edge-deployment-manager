# Control Plane API

The control plane issues **signed MQTT commands** to registered edge agents.

## Run locally

```bash
export CONTROL_PLANE_API_TOKEN="replace-with-long-random-token"
export EDGE_COMMAND_SIGNING_KEY_HEX="replace-with-ed25519-private-key-hex"

make run-control-plane
# or: edge-control-plane --config configs/control-plane.yaml
```

Default config: `configs/control-plane.yaml` (prod Compose uses `runtime/control-plane.yaml` from `make setup-dev`).

## Secrets

Production deployments should load secrets via `SecretProvider` (env, `*_FILE`, or `/run/secrets`). See [security-operations.md](security-operations.md).

## Registry storage

| `registry.backend` | Use case |
|--------------------|----------|
| `json` | Single instance, simple dev |
| `sqlite` | Persistent file registry (`make prod-up`) |
| `postgres` | Shared registry for HA (`make ha-up`, Helm) |

```yaml
registry:
  backend: postgres
  url_env: CONTROL_PLANE_DATABASE_URL
```

## HA mode

When `ha.enabled: true` (requires `postgres`):

- Only the **leader** replica publishes MQTT commands.
- Followers return `503` on `POST .../commands`.
- Check leadership: `GET /v1/leader`

See [ha-control-plane.md](ha-control-plane.md).

## API endpoints

Public (no bearer token):

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness (`is_leader` when HA enabled) |
| GET | `/metrics` | Prometheus metrics |

Authenticated (`Authorization: Bearer <CONTROL_PLANE_API_TOKEN>`):

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/leader` | Leadership status (HA) |
| GET | `/v1/devices` | List devices |
| POST | `/v1/devices` | Register device + policy |
| GET | `/v1/devices/{device_id}` | Get device |
| PUT | `/v1/devices/{device_id}/policy` | Update policy |
| POST | `/v1/devices/{device_id}/commands` | Sign and publish command (leader only when HA) |
| POST | `/v1/devices/{device_id}/certificates/rotate` | Rotate mTLS certificate |

Bootstrap (no bearer token; requires `X-Bootstrap-Token`):

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/bootstrap/enroll` | First-time enrollment |

Rate limits apply to authenticated and bootstrap routes. See [security-operations.md](security-operations.md).

## Register a device

```bash
curl -sS -X POST "http://127.0.0.1:8080/v1/devices" \
  -H "Authorization: Bearer ${CONTROL_PLANE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "edge-agent-001",
    "policy": {
      "allowed_actions": ["deploy"],
      "allowed_deployment_types": ["docker"],
      "allowed_images": ["nginx:*"]
    }
  }'
```

## Issue a deploy command

```bash
curl -sS -X POST "http://127.0.0.1:8080/v1/devices/edge-agent-001/commands" \
  -H "Authorization: Bearer ${CONTROL_PLANE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @examples/nginx-deploy-command.json
```

The control plane signs the envelope and publishes to `mqtt.command_topic` (default `edge/commands`).

## Bootstrap and rotation

- First enrollment: [tls-and-bootstrap.md](tls-and-bootstrap.md)
- Certificate rotation: `scripts/rotate_agent_cert.py` or `POST .../certificates/rotate`

## Agent trust configuration

After enrollment, the agent uses `runtime/agent-config.yaml` (Compose) or `security` in your config:

```yaml
security:
  device_id: "edge-agent-001"
  trusted_signers:
    - issuer: "control-plane"
      public_key_hex: "<public-key-hex>"
  replay_store:
    type: sqlite
    path: data/replay-nonces.db
```

## Persistence and audit

| Backend | Registry | Audit |
|---------|----------|-------|
| json | `data/devices.json` | `data/audit.log` |
| sqlite | `data/devices.db` | `data/audit.log` |
| postgres | PostgreSQL `devices` table | `data/audit.log` (file per replica) |
