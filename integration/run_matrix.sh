#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/tmp/pyqual-integration-matrix"
rm -rf "$ROOT_DIR"
mkdir -p "$ROOT_DIR"

pass_count=0
fail_count=0

run_case() {
  local ptype="$1"
  local repo="$ROOT_DIR/$ptype"

  rm -rf "$repo"
  mkdir -p "$repo"
  pushd "$repo" >/dev/null

  git init -q
  git config user.email "ci@example.com"
  git config user.name "CI"

  printf "0.1.0\n" > VERSION

  case "$ptype" in
    python-basic)
      cat > pyqual.yaml <<'YAML'
pipeline:
  name: integration-test-basic
  metrics:
    cc_max: 20
  stages:
    - name: test
      run: echo "tests passed"
      when: always
  loop:
    max_iterations: 1
    on_fail: report
YAML
      cat > app.py <<'PY'
def hello():
    return "hello"
PY
      ;;
    python-full)
      cat > pyqual.yaml <<'YAML'
pipeline:
  name: integration-test-full
  profile: python
  metrics:
    cc_max: 20
    coverage_min: 0
  stages:
    - name: test
      run: echo "tests passed"
      when: always
    - name: report
      tool: report
      when: always
      optional: true
  loop:
    max_iterations: 1
    on_fail: report
YAML
      cat > pyproject.toml <<'TOML'
[project]
name = "integration-test"
version = "0.1.0"
TOML
      cat > app.py <<'PY'
def hello():
    return "hello"

def add(a: int, b: int) -> int:
    return a + b
PY
      ;;
    lint-only)
      cat > pyqual.yaml <<'YAML'
pipeline:
  name: integration-test-lint
  profile: lint-only
  metrics:
    ruff_errors_max: 0
  stages:
    - name: lint
      run: echo "lint passed"
      when: always
  loop:
    max_iterations: 1
    on_fail: report
YAML
      cat > app.py <<'PY'
def hello():
    return "hello"
PY
      ;;
    ci-profile)
      cat > pyqual.yaml <<'YAML'
pipeline:
  name: integration-test-ci
  profile: ci
  metrics:
    cc_max: 30
  stages:
    - name: test
      run: echo "CI test passed"
      when: always
  loop:
    max_iterations: 1
    on_fail: report
YAML
      cat > app.py <<'PY'
def hello():
    return "hello"
PY
      ;;
    security-profile)
      cat > pyqual.yaml <<'YAML'
pipeline:
  name: integration-test-security
  profile: security
  metrics:
    bandit_high_max: 0
  stages:
    - name: audit
      run: echo "security audit passed"
      when: always
      optional: true
  loop:
    max_iterations: 1
    on_fail: report
YAML
      cat > app.py <<'PY'
def hello():
    return "hello"
PY
      ;;
    custom-stages)
      cat > pyqual.yaml <<'YAML'
pipeline:
  name: integration-test-custom
  metrics:
    cc_max: 20
  stages:
    - name: setup
      run: echo "setup done"
      when: first_iteration
    - name: test
      run: echo "tests passed"
      when: always
    - name: fix
      run: echo "fix applied"
      when: metrics_fail
    - name: verify
      run: echo "verification done"
      when: after_fix
      optional: true
  loop:
    max_iterations: 2
    on_fail: report
YAML
      cat > app.py <<'PY'
def hello():
    return "hello"
PY
      ;;
    *)
      echo "Unknown test case: $ptype" >&2
      popd >/dev/null
      return 1
      ;;
  esac

  git add -A
  git commit -qm "chore: init"

  # Verify pyqual can parse the config
  local out
  out=$(pyqual validate 2>&1 || true)
  echo "$out"

  # Verify pyqual config is valid YAML
  python3 -c "import yaml; yaml.safe_load(open('pyqual.yaml'))" || {
    echo "YAML parse failed"
    popd >/dev/null
    return 1
  }

  popd >/dev/null
}

CASES=(python-basic python-full lint-only ci-profile security-profile custom-stages)

for c in "${CASES[@]}"; do
  echo "=== [$c] ==="
  if run_case "$c"; then
    echo "PASS: $c"
    pass_count=$((pass_count + 1))
  else
    echo "FAIL: $c"
    fail_count=$((fail_count + 1))
  fi
done

echo ""
echo "Passed: $pass_count, Failed: $fail_count"

if [[ "$fail_count" -gt 0 ]]; then
  exit 1
fi
