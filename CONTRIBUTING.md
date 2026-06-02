# Contributing

Thanks for contributing to Edge Deployment Manager.

## Setup

```bash
git clone https://github.com/akintunero/edge-deployment-manager.git
cd edge-deployment-manager
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e ".[postgres,redis]"
```

Optional full stack for manual testing:

```bash
make setup-dev
make prod-up
make prod-deploy-example
make prod-down
```

## Before you open a PR

```bash
make test
make ci-lint
make ci-typecheck    # same as CI on Python 3.12
```

For stack changes, run E2E locally when Docker is available:

```bash
make prod-up
make e2e-test
make prod-down
```

Use the [pull request template](.github/pull_request_template.md). Update docs when behavior, config, or APIs change.

## Code expectations

- PEP 8, type hints on new code, `make ci-lint` clean
- Unit tests for behavior changes (`tests/`)
- No secrets in commits (use `.env`, `/run/secrets`, or CI secrets)
- Security-sensitive paths: signed commands, bootstrap, registry, TLS — see [SECURITY.md](SECURITY.md)

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(control-plane): add device heartbeat endpoint
fix(agent): reconnect MQTT after broker restart
docs: update HA control plane guide
```

## Project layout

```
src/
  manager.py                 # edge agent entry
  control_plane/             # API, registry, bootstrap, HA
  command_security.py        # envelope verify/sign helpers
configs/                     # sample YAML
deploy/helm/edge-stack/      # Helm chart
docs/                        # guides (start at docs/README.md)
examples/                    # sample payloads and scripts
scripts/                     # setup_dev, enroll, e2e, PKI
tests/
```

## Releases (maintainers)

See [docs/guides/releasing.md](docs/guides/releasing.md). Summary:

1. Update `CHANGELOG.md`, `pyproject.toml`, and `src/__init__.py` version
2. `make release-check`
3. Tag `v*` and push (release workflow publishes to PyPI when configured)

## Community

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md) — report vulnerabilities privately
- GitHub Issues for bugs, features, and questions

Maintainer: Olúmáyòwá Akinkuehinmi — [akintunero101@gmail.com](mailto:akintunero101@gmail.com)
