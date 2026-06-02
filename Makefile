# Makefile for Edge Deployment Manager
# Common development tasks and shortcuts

.PHONY: help install install-dev test test-cov lint format clean docs build check-all setup-dev prod-up prod-down prod-deploy-example

# Default target
help:
	@echo "Edge Deployment Manager - Development Commands"
	@echo "=============================================="
	@echo ""
	@echo "Installation:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test         - Run all tests"
	@echo "  test-cov     - Run tests with coverage report"
	@echo "  test-fast    - Run tests without coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black and isort"
	@echo "  type-check   - Run type checking with mypy"
	@echo "  security     - Run security checks"
	@echo ""
	@echo "Development:"
	@echo "  clean        - Clean build artifacts"
	@echo "  docs         - Build documentation"
	@echo "  build        - Build package"
	@echo "  check-all    - Run all quality checks"
	@echo ""
	@echo "Application:"
	@echo "  run          - Run the application"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

# Testing
test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ --cov=src --cov-report=html --cov-report=term

test-fast:
	python -m pytest tests/ -v --tb=short

# Code Quality
lint:
	flake8 src/ --max-line-length=120 --ignore=E501,W503
	black --check src/ --line-length=120
	isort --check-only src/ --profile=black --line-length=120

format:
	black src/ --line-length=120
	isort src/ --profile=black --line-length=120

type-check:
	mypy src/

security:
	bandit -r src/ -f json -o bandit-report.json
	safety scan

# Development
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:
	cd docs && make html

build:
	python -m build

check-all: lint type-check security test

ci-check-all: ci-lint ci-typecheck ci-security ci-test
	@echo "✅ All checks passed!"

# Application
run:
	python -m src.manager

run-control-plane:
	python -m src.control_plane.main --config configs/control-plane.yaml

generate-pki:
	python3 scripts/generate_pki.py --output-dir certs

docker-build:
	docker build -t edge-deployment-manager .

docker-run:
	docker run -it --rm edge-deployment-manager

# CI/CD
ci-install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

ci-test:
	python -m pytest tests/ --cov=src --cov-report=xml

ci-lint:
	flake8 src/ --max-line-length=120 --ignore=E501,W503
	black --check src/ --line-length=120 --target-version py312
	isort --check-only src/ --profile=black --line-length=120

ci-typecheck:
	mypy src/

ci-security:
	bandit -r src/ -f json -o bandit-report.json
	safety scan

# Development helpers
setup-dev:
	python3 scripts/setup_dev.py

prod-up: setup-dev
	docker compose -f docker-compose.prod.yml up -d --build mosquitto control-plane
	python3 scripts/wait_and_enroll.py
	docker compose -f docker-compose.prod.yml up -d --build edge-agent
	@echo "Production stack is up:"
	@echo "  Control plane: https://localhost:8080/health"
	@echo "  Agent metrics: http://localhost:9090/metrics"

prod-down:
	docker compose -f docker-compose.prod.yml down

ha-up: setup-dev
	docker compose -f docker-compose.ha.yml up -d --build postgres mosquitto control-plane-a control-plane-b
	@echo "HA control plane:"
	@echo "  Replica A: https://localhost:8080/v1/leader"
	@echo "  Replica B: https://localhost:8081/v1/leader"

ha-down:
	docker compose -f docker-compose.ha.yml down

e2e-test:
	python3 scripts/e2e_stack_test.py --timeout 240

prod-deploy-example:
	@test -n "$$(grep CONTROL_PLANE_API_TOKEN .env | cut -d= -f2)" || (echo "Run make setup-dev first" && exit 1)
	curl -sk -X POST "https://localhost:8080/v1/devices/edge-agent-001/commands" \
		-H "Authorization: Bearer $$(grep CONTROL_PLANE_API_TOKEN .env | cut -d= -f2)" \
		-H "Content-Type: application/json" \
		-d @examples/nginx-deploy-command.json

setup-dev-legacy: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify installation"

quick-test: format lint test
	@echo "✅ Quick test complete!"

# Git helpers
pre-commit: format lint type-check test
	@echo "✅ Pre-commit checks complete!"

# Release helpers
lock-deps:
	pip install pip-tools
	python3 scripts/lock_requirements.py

release-check: clean check-all build
	@echo "✅ Release checks complete!"

# Docker helpers
docker-clean:
	docker system prune -f
	docker image prune -f

# Monitoring
logs:
	tail -f logs/edge-manager.log

# Database helpers (if applicable)
db-migrate:
	@echo "Database migrations not implemented yet"

db-seed:
	@echo "Database seeding not implemented yet" 