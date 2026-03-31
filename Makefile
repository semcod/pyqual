.PHONY: help install install-dev test lint format clean build bump-patch bump-minor publish upload

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
	@echo "  bump-patch   Bump patch version (0.1.2 -> 0.1.3)"
	@echo "  bump-minor   Bump minor version (0.1.2 -> 0.2.0)"
	@echo "  publish      Bump version, build and publish to PyPI"
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

# Bump patch version (0.1.2 -> 0.1.3)
bump-patch:
	@echo "Bumping patch version..."
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	PATCH=$$(echo $$CURRENT | cut -d. -f3); \
	NEW_PATCH=$$((PATCH + 1)); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	echo "$$NEW_VERSION" > VERSION; \
	sed -i "s/version = \"$$CURRENT\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo "Version bumped: $$CURRENT -> $$NEW_VERSION"

# Bump minor version (0.1.2 -> 0.2.0)
bump-minor:
	@echo "Bumping minor version..."
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	NEW_MINOR=$$((MINOR + 1)); \
	NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	sed -i "s/version = \"$$CURRENT\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo "Version bumped: $$CURRENT -> $$NEW_VERSION"

# Build and publish to PyPI (auto-bumps patch version)
publish: bump-patch build
	venv/bin/python -m twine upload dist/*

# Upload to PyPI (alias)
upload: publish
