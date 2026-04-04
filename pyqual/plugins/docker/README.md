# Docker Plugin

Container security scanning and Dockerfile linting for pyqual.

## Overview

The Docker plugin provides security scanning for container images and linting for Dockerfiles:

- **trivy** — Comprehensive vulnerability scanner for containers
- **hadolint** — Dockerfile linter (best practices enforcement)
- **grype** — Alternative vulnerability scanner from Anchore

## Installation

```bash
# Install trivy
# See: https://aquasecurity.github.io/trivy/latest/getting-started/installation/

# Install hadolint
# See: https://github.com/hadolint/hadolint#install

# Install grype (optional, alternative to trivy)
# See: https://github.com/anchore/grype#installation
```

## Metrics Collected

| Metric | Description | Default Max |
|--------|-------------|-------------|
| `docker_vuln_critical` | Trivy CRITICAL CVEs | 0 |
| `docker_vuln_high` | Trivy HIGH CVEs | 5 |
| `docker_vuln_medium` | Trivy MEDIUM CVEs | 20 |
| `docker_vuln_low` | Trivy LOW CVEs | ∞ |
| `docker_hadolint_errors` | Dockerfile lint errors | 0 |
| `docker_hadolint_warnings` | Dockerfile lint warnings | ∞ |
| `docker_grype_critical` | Grype Critical CVEs | 0 |
| `docker_grype_high` | Grype High CVEs | 0 |
| `docker_image_size_mb` | Image size in MB | 500 |
| `docker_layer_count` | Number of image layers | ∞ |

## Configuration Example

```yaml
pipeline:
  name: docker-security

  metrics:
    docker_vuln_critical_max: 0
    docker_vuln_high_max: 5
    docker_hadolint_errors_max: 0
    docker_image_size_max_mb: 500

  stages:
    - name: dockerfile_lint
      run: hadolint Dockerfile --format json > .pyqual/hadolint.json 2>&1 || true
      when: always
      optional: true

    - name: image_scan
      run: |
        docker build -t myapp:latest .
        trivy image --format json -o .pyqual/trivy.json myapp:latest
      when: always
      optional: true
      timeout: 600

    - name: image_info
      run: docker inspect myapp:latest > .pyqual/docker_image.json
      when: always
      optional: true

  loop:
    max_iterations: 1
```

## Programmatic API

```python
from pyqual.plugins.docker import (
    DockerCollector,
    run_hadolint,
    run_trivy_scan,
    docker_security_check,
    get_image_info,
)

# Lint Dockerfile
lint_result = run_hadolint("Dockerfile")
print(f"Errors: {lint_result['error_count']}, Warnings: {lint_result['warning_count']}")

# Scan image for vulnerabilities
scan_result = run_trivy_scan("myapp:latest")
print(f"Critical: {scan_result['critical_count']}, High: {scan_result['high_count']}")

# Get comprehensive security check
security = docker_security_check(
    image="myapp:latest",
    dockerfile="Dockerfile"
)
print(f"Secure: {security['is_secure']}")

# Get image size and layer info
info = get_image_info("myapp:latest")
print(f"Size: {info['size_mb']} MB, Layers: {info['layer_count']}")
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Docker Security Scan
  run: |
    pyqual run --stage dockerfile_lint
    pyqual run --stage image_scan
```

### GitLab CI

```yaml
docker-security:
  script:
    - hadolint Dockerfile --format json -o .pyqual/hadolint.json || true
    - trivy image --format json -o .pyqual/trivy.json $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
```

## Tags

- `docker`
- `container`
- `security`
- `vulnerability`
- `lint`
- `image`

## Version

1.0.0
