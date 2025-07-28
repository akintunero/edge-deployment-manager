# Contributing to Edge Deployment Manager

Thank you for your interest in contributing to the Edge Deployment Manager! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Getting Started

1. **Fork the Repository**
   ```bash
   git clone https://github.com/akintunero/edge-deployment-manager.git
   cd edge-deployment-manager
   ```

2. **Set Up Development Environment**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate  # On Windows
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```

3. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

### Development Guidelines

#### Code Style
- Follow **PEP 8** style guidelines
- Use **type hints** for all function parameters and return values
- Keep functions focused and **single-purpose**
- Add **docstrings** for all classes and methods
- Use **descriptive variable names**

#### Testing
- Write **unit tests** for new functionality
- Ensure **100% test coverage** for new code
- Run tests before submitting:
  ```bash
   python3 -m pytest tests/ -v
   python3 -m pytest tests/ --cov=src --cov-report=html
   ```

#### Code Quality
- Run linting checks:
  ```bash
   python3 -m flake8 src/ --max-line-length=120
   python3 -m black src/ --line-length=120
   ```
- Fix any linting errors before submitting

### Commit Message Guidelines

Use **conventional commit format**:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat: add Kubernetes namespace management"
git commit -m "fix: resolve MQTT connection timeout issue"
git commit -m "docs: update README with deployment examples"
git commit -m "test: add unit tests for Docker handler"
```

### Pull Request Process

1. **Update Documentation**
   - Update README.md if needed
   - Add docstrings for new functions
   - Update any relevant configuration examples

2. **Test Your Changes**
   ```bash
   # Run all tests
   python3 -m pytest tests/ -v
   
   # Run linting
   python3 -m flake8 src/ --max-line-length=120
   
   # Test application startup
   python3 src/manager.py
   ```

3. **Submit Pull Request**
   - Use a descriptive title
   - Include detailed description of changes
   - Reference any related issues
   - Add screenshots if UI changes

### Issue Reporting

When reporting issues, please include:

1. **Environment Information**
   ```bash
   python3 --version
   docker --version
   kubectl version --client
   ```

2. **Steps to Reproduce**
   - Clear, step-by-step instructions
   - Include configuration files if relevant

3. **Expected vs Actual Behavior**
   - What you expected to happen
   - What actually happened

4. **Error Messages**
   - Full error traceback
   - Log files if available

### Development Setup

#### Prerequisites
- Python 3.8+
- Docker
- Kubernetes cluster (optional)
- MQTT broker (optional)

#### Local Development
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests with coverage
python3 -m pytest tests/ --cov=src --cov-report=html

# Run linting
python3 -m flake8 src/ --max-line-length=120

# Format code
python3 -m black src/ --line-length=120
```

### Project Structure

```
edge-deployment-manager/
├── src/                    # Source code
│   ├── manager.py         # Main deployment manager
│   ├── mqtt_handler.py    # MQTT communication
│   ├── docker_handler.py  # Docker operations
│   ├── k8s_controller.py  # Kubernetes integration
│   └── __init__.py
├── tests/                 # Unit tests
├── configs/              # Configuration files
├── docs/                 # Documentation
├── examples/             # Usage examples
└── requirements.txt      # Dependencies
```

### Adding New Features

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-feature-name
   ```

2. **Implement Feature**
   - Add code in appropriate module
   - Add comprehensive tests
   - Update documentation

3. **Test Thoroughly**
   ```bash
   python3 -m pytest tests/ -v
   python3 -m flake8 src/ --max-line-length=120
   ```

4. **Update Documentation**
   - Add docstrings
   - Update README if needed
   - Add usage examples

### Bug Fixes

1. **Reproduce the Bug**
   - Create minimal test case
   - Document steps to reproduce

2. **Fix the Issue**
   - Implement the fix
   - Add regression tests

3. **Test the Fix**
   ```bash
   python3 -m pytest tests/ -v
   ```

### Code Review Process

1. **Self-Review**
   - Check your code follows guidelines
   - Ensure all tests pass
   - Verify documentation is updated

2. **Submit for Review**
   - Create descriptive PR
   - Respond to review comments
   - Make requested changes

3. **Merge**
   - Squash commits if needed
   - Ensure CI/CD passes
   - Update changelog

### Release Process

1. **Version Bumping**
   - Update version in `__init__.py`
   - Update CHANGELOG.md

2. **Testing Release**
   ```bash
   python3 -m pytest tests/ -v
   python3 src/manager.py --version
   ```

3. **Creating Release**
   - Tag the release
   - Write release notes
   - Publish to PyPI (if applicable)

### Communication

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Pull Requests**: For code contributions

### Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Please read our [Code of Conduct](CODE_OF_CONDUCT.md) for details.

### License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Contact

For questions about contributing or the project in general:

- **Email**: [akintunero101@gmail.com](mailto:akintunero101@gmail.com)
- **GitHub Issues**: [Create an issue](https://github.com/akintunero/edge-deployment-manager/issues)
- **GitHub Discussions**: [Start a discussion](https://github.com/akintunero/edge-deployment-manager/discussions)

## Acknowledgments

Thank you to all contributors who help make Edge Deployment Manager better!

---

Thank you for contributing to Edge Deployment Manager! 🚀

**Maintainer**: Olúmáyòwá Akinkuehinmi - [akintunero101@gmail.com](mailto:akintunero101@gmail.com) 