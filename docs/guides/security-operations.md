# Security operations (Phase 1)

## Secret loading

Secrets resolve in this order:

1. Environment variable (development)
2. `EDGE_SECRETS_DIR/<NAME>` file (default `/run/secrets/<NAME>`)
3. `<NAME>_FILE` pointing at a mounted secret file

Control plane keys:

| Name | Purpose |
|------|---------|
| `CONTROL_PLANE_API_TOKEN` | Bearer token for API |
| `EDGE_COMMAND_SIGNING_KEY_HEX` | Ed25519 private key (hex) |
| `EDGE_BOOTSTRAP_TOKEN` | Bootstrap enrollment (or use hash below) |
| `EDGE_BOOTSTRAP_TOKEN_HASH` | sha256 hex of bootstrap token |

```yaml
secrets:
  directory: /run/secrets
```

## API rate limits

```yaml
server:
  rate_limit:
    enabled: true
    max_requests: 120
    window_seconds: 60

bootstrap:
  rate_limit:
    enabled: true
    max_requests: 10
    window_seconds: 60
```

Returns `429` when exceeded.

## Distributed command replay protection

For multiple agent replicas per device, use Redis:

```yaml
security:
  replay_store:
    type: redis
    url_env: EDGE_REDIS_URL
    key_prefix: edge:nonce
```

Install: `pip install 'edge-deployment-manager[redis]'`

Per-agent SQLite remains the default for single-replica agents.

## Certificate rotation

Enrolled devices can rotate mTLS certificates without re-registering:

```bash
python3 scripts/rotate_agent_cert.py \
  --control-plane-url "https://control-plane:8080" \
  --device-id "edge-agent-001" \
  --api-token "${CONTROL_PLANE_API_TOKEN}" \
  --credential-dir "./runtime/agent-credentials"
```

API: `POST /v1/devices/{device_id}/certificates/rotate` with body `{"csr_pem":"..."}`.

Restart the agent or reload MQTT TLS files after rotation.

## Rotation schedule

- Issue client certs with shorter TTL in production (`bootstrap.cert_validity_days`).
- Rotate before expiry (30-day threshold available via `inspect_certificate_pem`).
