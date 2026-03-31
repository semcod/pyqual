.PHONY: help install install-dev test lint format clean build publish upload

# Default target
help:
	@echo "Available targets:"
	@echo "  install      Install the package"
	@echo "  install-dev  Install the package with dev dependencies"
	@echo "  test         Run tests"
	@echo "  lint         Run linting"
	@echo "  format       Format code"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build the package"
	@echo "  publish      Build and publish to PyPI"
	@echo "  upload       Upload to PyPI (alias for publish)"

# Install the package
install:
	pip3 install -e .

# Install with dev dependencies
install-dev:
	pip3 install -e ".[dev]"

# Run tests
test:
	python3 -m pytest

# Run linting
lint:
	ruff check .
	mypy pyqual

# Format code
format:
	ruff format .

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -not -path "./.venv/*" -delete

# Build the package
build: clean
	venv/bin/python -m build

# Build and publish to PyPI
publish: build
	venv/bin/python -m twine upload dist/*

# Upload to PyPI (alias)
upload: publish
