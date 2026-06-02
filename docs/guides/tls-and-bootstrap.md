# TLS, mTLS, and Device Bootstrap

Production deployments should use TLS for MQTT and the control plane API, plus mTLS
for edge agents connecting to MQTT.

## 1. Generate PKI assets

```bash
python3 scripts/generate_pki.py --output-dir certs
```

This creates:

- `certs/ca.crt` / `certs/ca.key` (internal CA)
- `certs/mqtt-server.crt` / `certs/mqtt-server.key` (Mosquitto broker)
- `certs/control-plane.crt` / `certs/control-plane.key` (HTTPS API)
- `certs/control-plane-mqtt.crt` / `certs/control-plane-mqtt.key` (control plane MQTT client)

## 2. Enable Mosquitto mTLS

Use `configs/mosquitto.tls.conf` as a starting point and mount generated certificates.

## 3. Enable control plane TLS

In `configs/control-plane.yaml`:

```yaml
server:
  tls:
    enabled: true
    cert_file: "certs/control-plane.crt"
    key_file: "certs/control-plane.key"
    ca_cert: "certs/ca.crt"
    require_client_cert: false

mqtt:
  port: 8883
  tls:
    enabled: true
    ca_cert: "certs/ca.crt"
    cert_file: "certs/control-plane-mqtt.crt"
    key_file: "certs/control-plane-mqtt.key"
```

Set:

```bash
export CONTROL_PLANE_API_TOKEN="..."
export EDGE_BOOTSTRAP_TOKEN="..."
export EDGE_COMMAND_SIGNING_KEY_HEX="..."
```

## 4. Bootstrap enroll an agent

```bash
python3 scripts/agent_enroll.py \
  --control-plane-url "https://127.0.0.1:8080" \
  --device-id "edge-agent-001" \
  --bootstrap-token "${EDGE_BOOTSTRAP_TOKEN}" \
  --credential-dir "./edge-credentials"
```

Or call the API directly:

```bash
curl -sS -X POST "https://127.0.0.1:8080/v1/bootstrap/enroll" \
  -H "X-Bootstrap-Token: ${EDGE_BOOTSTRAP_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"edge-agent-001","csr_pem":"..."}'
```

The response includes:

- Issued client certificate + CA chain (PEM)
- Suggested `agent_config` (Compose writes `runtime/agent-config.yaml`)
- Credential file paths (`/etc/edge/...`)

## 5. Run the edge agent with mTLS

Copy credentials to the agent host and align `mqtt.tls` paths and `security.device_id` /
`trusted_signers` with enrollment output (`runtime/agent-config.yaml` when using `make prod-up`).

## Security notes

- Keep `certs/ca.key` offline and protected.
- Rotate bootstrap tokens after initial fleet enrollment.
- Do not enable `tls.insecure` outside local development.
- Bootstrap endpoint does not use the API token; it requires `X-Bootstrap-Token`.
- Prefer storing `EDGE_BOOTSTRAP_TOKEN_HASH` (sha256 hex) via `bootstrap.token_hash_env` instead of a plain token in production.
- Bootstrap requests are rate-limited (`bootstrap.rate_limit` in control plane config).
- Invalid bootstrap tokens return `401` with a generic error (`bootstrap enrollment denied`).
- Edge agents persist command nonces in SQLite (`security.replay_store`) so replays are rejected across restarts.

### Replay protection (agents)

```yaml
security:
  replay_store:
    type: sqlite
    path: data/replay-nonces.db
```

Use `type: memory` only for local development.

### Bootstrap rate limit (control plane)

```yaml
bootstrap:
  rate_limit:
    enabled: true
    max_requests: 10
    window_seconds: 60
```
