# Makefile for Edge Deployment Manager
# Common development tasks and shortcuts

.PHONY: help install install-dev test test-cov lint format clean docs build check-all

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
	safety check

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
	@echo "✅ All checks passed!"

# Application
run:
	python src/manager.py

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
	black --check src/ --line-length=120
	isort --check-only src/ --profile=black --line-length=120

ci-security:
	bandit -r src/ -f json -o bandit-report.json
	safety check

# Development helpers
setup-dev: install-dev
	@echo "✅ Development environment setup complete!"
	@echo "Run 'make test' to verify installation"

quick-test: format lint test
	@echo "✅ Quick test complete!"

# Git helpers
pre-commit: format lint type-check test
	@echo "✅ Pre-commit checks complete!"

# Release helpers
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