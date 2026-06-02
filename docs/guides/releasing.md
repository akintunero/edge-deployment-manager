# Releasing

## Versioning

- Package version lives in `pyproject.toml` (`[project].version`) and `src/__init__.py`.
- Follow [Semantic Versioning](https://semver.org/) and update `CHANGELOG.md` under `[Unreleased]`.

## Local release checks

```bash
make release-check
```

Runs lint, type-check, security scans, tests, and `python -m build`.

## Pin dependencies (optional)

```bash
pip install pip-tools
python3 scripts/lock_requirements.py
```

Commit updated `requirements.lock` / `requirements-dev.lock` when refreshing pins.

## Publish to PyPI (maintainers)

### Trusted publishing (recommended)

1. Create the PyPI project `edge-deployment-manager` (if it does not exist).
2. On PyPI → **Publishing** → **Add a new pending publisher**:
   - PyPI project name: `edge-deployment-manager`
   - Owner: `akintunero`
   - Repository: `edge-deployment-manager`
   - Workflow: `release.yml`
   - Environment name: `pypi`
3. In GitHub → **Settings → Environments** → create environment `pypi` (no extra secrets required for OIDC).
4. Tag a release (workflow validates tests, builds, publishes, creates GitHub release):

```bash
git tag v2.0.0
git push origin v2.0.0
```

### Manual checklist before tagging

- [ ] `CHANGELOG.md` updated
- [ ] `pyproject.toml` and `src/__init__.py` versions match tag
- [ ] `make release-check` passes locally
- [ ] `requirements.lock` refreshed if dependencies changed (`make lock-deps`)

### Legacy steps

1. Configure a GitHub **environment** named `pypi` with [trusted publishing](https://docs.pypi.org/trusted-publishers/) for this repository.
2. Tag a release:

```bash
git tag v2.0.0
git push origin v2.0.0
```

3. The [Release workflow](https://github.com/akintunero/edge-deployment-manager/actions) runs tests, builds sdist/wheel, publishes to PyPI, and creates a GitHub release.

## Install from PyPI

```bash
pip install edge-deployment-manager
edge-deployment-manager --help
edge-control-plane --help
```
