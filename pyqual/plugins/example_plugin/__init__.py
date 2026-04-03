"""Example plugin package for pyqual."""

from __future__ import annotations

from pyqual.plugins.example_plugin.main import (
    ExampleCollector,
    example_helper_function,
)

__all__ = [
    "ExampleCollector",
    "example_helper_function",
]
