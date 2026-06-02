# Changelog

All notable changes to the Edge Deployment Manager project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Control plane with signed MQTT command issuance, device registry, and audit log
- Edge agent with Docker/Kubernetes deploy actions, health/metrics endpoints, MQTT reconnect
- Security: Ed25519 signed commands, mTLS bootstrap, durable replay store (SQLite/Redis), API rate limits, cert rotation
- HA: PostgreSQL registry, leader election, `docker-compose.ha.yml` (`make ha-up`)
- Production stack: `make prod-up`, `scripts/setup_dev.py`, `scripts/e2e_stack_test.py`, E2E CI workflow
- Helm chart `deploy/helm/edge-stack` (Postgres, Mosquitto, control plane, edge agent)
- `SecretProvider`, Dependabot, issue/PR templates, release workflow, committed lock files
- Docs: architecture, production quickstart, security/HA guides; README rewrite

### Changed
- Kubernetes manifests apply via dynamic client (create-or-replace)
- CI: lint, security scan, mypy (3.12), tests, Codecov artifact
- Local prod Compose uses SQLite registry; HA Compose uses PostgreSQL

## [2.0.0] - 2025-07-27

### Added
- **Major Refactor**: Complete rewrite of all components
- **MQTT Handler**: Modern client with v3.1.1 protocol support
- **Docker Handler**: Full container lifecycle management
- **Kubernetes Controller**: Multi-resource deployment support
- **Edge Deployment Manager**: Main orchestration component
- **Testing**: Initial pytest suite (superseded by expanded coverage in later releases)
- **Error Handling**: Graceful error recovery throughout
- **Logging**: Configurable logging with multiple levels
- **Configuration**: Enhanced YAML-based configuration
- **Documentation**: Complete README with examples

### Changed
- **Architecture**: Modular design with separate handlers
- **MQTT Protocol**: Updated to MQTT v3.1.1
- **Code Quality**: Added type hints and docstrings
- **Testing**: Comprehensive test suite with mocks
- **Dependencies**: Updated with version constraints

### Fixed
- **MQTT Compatibility**: Fixed deprecated API usage
- **Import Issues**: Resolved module import problems
- **Code Style**: Applied PEP 8 and Black formatting
- **Configuration**: Fixed YAML parsing and loading
- **Error Handling**: Added comprehensive try-catch blocks

## [1.0.0] - 2025-01-15

### Added
- Initial release of Edge Deployment Manager
- Basic MQTT client implementation
- Simple Docker container management
- Basic Kubernetes integration
- Configuration file support
- Basic logging functionality

### Known Issues
- MQTT client uses deprecated API
- Limited error handling
- No comprehensive testing
- Basic documentation only

---

## Version History

- **v2.0.0**: Major refactor with production-ready features
- **v1.0.0**: Initial release with basic functionality

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).