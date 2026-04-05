"""Pyqual dependency checker and installer.

Called via ``tool: setup-deps`` in pyqual.yaml — or directly:

    python3 -m pyqual.setup_deps

Checks which pipeline dependencies are installed and optionally installs
missing ones. Works as a graceful gate: never fails the pipeline.

Checked tools:
  pip packages: code2llm, vallm, prefact, llx, pytest-cov, goal, pip-audit,
                detect-secrets, bandit
  cli tools:    ruff, mypy, claude, git
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class DepResult:
    """Result of a single dependency check."""
    name: str
    installed: bool
    version: str = ""
    install_attempted: bool = False
    install_ok: bool = False


_PIP_PACKAGES = [
    "code2llm",
    "vallm",
    "prefact",
    "llx",
    "pytest-cov",
    "goal",
    "pip-audit",
    "detect-secrets",
    "bandit",
    "ruff",
    "mypy",
]

_CLI_TOOLS = [
    "git",
    "claude",
    "make",
    "twine",
]


def _check_pip(package: str) -> DepResult:
    """Check if a pip package is installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            version = ""
            for line in result.stdout.splitlines():
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                    break
            return DepResult(name=package, installed=True, version=version)
    except Exception:
        pass
    return DepResult(name=package, installed=False)


def _check_cli(tool: str) -> DepResult:
    """Check if a CLI tool is available in PATH."""
    path = shutil.which(tool)
    return DepResult(name=tool, installed=path is not None)


def _install_pip(package: str) -> bool:
    """Attempt to pip-install a package. Returns True on success."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", package],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_all(install_missing: bool = False) -> list[DepResult]:
    """Check all dependencies and optionally install missing pip packages."""
    results: list[DepResult] = []

    for pkg in _PIP_PACKAGES:
        dep = _check_pip(pkg)
        if not dep.installed and install_missing:
            dep.install_attempted = True
            dep.install_ok = _install_pip(pkg)
            dep.installed = dep.install_ok
        results.append(dep)

    for tool in _CLI_TOOLS:
        results.append(_check_cli(tool))

    return results


def main() -> int:
    """Check and report dependency status."""
    install = "--install" in sys.argv or "-i" in sys.argv
    results = check_all(install_missing=install)

    ok_count = sum(1 for r in results if r.installed)
    total = len(results)

    print(f"=== pyqual dependency check ({ok_count}/{total} available) ===")
    for dep in results:
        if dep.installed:
            ver = f" v{dep.version}" if dep.version else ""
            print(f"  ✓ {dep.name}{ver}")
        elif dep.install_attempted:
            status = "✓ installed" if dep.install_ok else "✗ install failed"
            print(f"  {status}: {dep.name}")
        else:
            hint = " (optional)" if dep.name in {"claude", "make", "twine", "goal"} else ""
            print(f"  ✗ {dep.name}{hint}")

    print("=== setup done ===")
    return 0  # always succeed — missing tools are handled gracefully per-stage


if __name__ == "__main__":
    sys.exit(main())
