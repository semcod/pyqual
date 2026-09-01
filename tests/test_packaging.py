"""Regression coverage for the published package layout."""

from pathlib import Path

from setuptools.config.pyprojecttoml import load_file
from setuptools.discovery import PEP420PackageFinder


ROOT = Path(__file__).resolve().parents[1]


def test_setuptools_discovers_cli_and_runtime_subpackages() -> None:
    """The wheel must contain every package used by the console entry point."""
    configuration = load_file(ROOT / "pyproject.toml")
    package_config = configuration["tool"]["setuptools"]["packages"]

    assert package_config == {"find": {"include": ["pyqual*"]}}
    assert configuration["tool"]["setuptools"]["exclude-package-data"] == {
        "*": ["*.bak"]
    }
    source_manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "global-exclude *.bak" in source_manifest
    assert "exclude .aider.chat.history.md" in source_manifest
    assert "prune .pyqual" in source_manifest
    assert "prune code2llm_output" in source_manifest

    discovered = set(
        PEP420PackageFinder.find(where=ROOT, include=("pyqual*",))
    )
    assert {
        "pyqual",
        "pyqual.bulk",
        "pyqual.cli",
        "pyqual.fix_tools",
        "pyqual.gate_collectors",
        "pyqual.integrations",
        "pyqual.plugins",
        "pyqual.validation",
    } <= discovered
