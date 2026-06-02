# Edge Deployment Manager

Signed, policy-bound application deployments for edge fleets over **MQTT**, with a small **control plane** and **edge agent**.

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![CI](https://github.com/akintunero/edge-deployment-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/akintunero/edge-deployment-manager/actions/workflows/ci.yml)
[![E2E](https://github.com/akintunero/edge-deployment-manager/actions/workflows/e2e.yml/badge.svg)](https://github.com/akintunero/edge-deployment-manager/actions/workflows/e2e.yml)

## What it does

- **Control plane** — device registry, per-device policy, bootstrap (mTLS certs), signed command API
- **Edge agent** — verifies commands, deploys via Docker or Kubernetes manifests
- **Security** — Ed25519 signatures, nonce replay protection, mTLS MQTT, API rate limits, cert rotation

## Quick start (local production stack)

**Prerequisites:** Docker, Python 3.10+

```bash
git clone https://github.com/akintunero/edge-deployment-manager.git
cd edge-deployment-manager
pip install -r requirements.txt
pip install -e .

make prod-up          # PKI, enroll agent, start stack
make prod-deploy-example
curl -s http://localhost:8088   # nginx demo
make prod-down
```

Details: [docs/guides/production-quickstart.md](docs/guides/production-quickstart.md)

## CLI entry points

| Command | Purpose |
|---------|---------|
| `edge-deployment-manager` | Edge agent |
| `edge-control-plane` | Control plane API |

## Documentation

| Topic | Guide |
|-------|--------|
| Architecture | [docs/architecture.md](docs/architecture.md) |
| Production roadmap (3 phases) | [docs/PRODUCTION_ROADMAP.md](docs/PRODUCTION_ROADMAP.md) |
| Control plane API | [docs/guides/control-plane.md](docs/guides/control-plane.md) |
| Command security | [docs/guides/command-security.md](docs/guides/command-security.md) |
| TLS & bootstrap | [docs/guides/tls-and-bootstrap.md](docs/guides/tls-and-bootstrap.md) |
| Security operations | [docs/guides/security-operations.md](docs/guides/security-operations.md) |
| HA control plane | [docs/guides/ha-control-plane.md](docs/guides/ha-control-plane.md) |
| Helm deployment | [deploy/helm/edge-stack/README.md](deploy/helm/edge-stack/README.md) |
| Releases & PyPI | [docs/guides/releasing.md](docs/guides/releasing.md) |
| Examples | [examples/README.md](examples/README.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Development

```bash
pip install -r requirements-dev.txt
pip install -e ".[postgres,redis]"   # optional HA / replay backends
make test
make ci-lint
make ci-typecheck
make lock-deps   # refresh requirements.lock
make e2e-test    # requires running prod stack locally
```

## HA stack (two control planes + Postgres)

```bash
make ha-up
# https://localhost:8080 and https://localhost:8081
```

## Optional extras

```bash
pip install "edge-deployment-manager[postgres]"  # HA registry
pip install "edge-deployment-manager[redis]"     # distributed replay store
```

## License

MIT — see [LICENSE](LICENSE).
