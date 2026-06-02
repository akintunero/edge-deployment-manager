# Examples

Sample artifacts for local development and the production Compose stack.

## Recommended (current stack)

### `nginx-deploy-command.json`

Signed deploy command body used by `make prod-deploy-example` and `scripts/e2e_stack_test.py`.

```bash
curl -sk -X POST "https://localhost:8080/v1/devices/edge-agent-001/commands" \
  -H "Authorization: Bearer ${CONTROL_PLANE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @examples/nginx-deploy-command.json
```

Policy must allow the image (`nginx:*` in default prod policy). The agent deploys a container named `nginx-edge-demo` on host port `8088`.

## Legacy (direct handler demo)

### `basic-deployment.py`

Standalone script that calls `DockerHandler` / `KubernetesController` directly without the control plane or signed MQTT flow. Useful for debugging handlers only; **not** the production deployment path.

```bash
# from repo root, with Docker running
python3 examples/basic-deployment.py
```

For production-style workflows use [production-quickstart](../docs/guides/production-quickstart.md) instead.

## Related scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup_dev.py` | PKI, `.env`, runtime configs |
| `scripts/wait_and_enroll.py` | Bootstrap enroll agent |
| `scripts/e2e_stack_test.py` | Post-deploy verification |
| `scripts/rotate_agent_cert.py` | mTLS certificate rotation |
| `scripts/generate_pki.py` | Generate CA and server certs |
