#!/usr/bin/env python3
"""Minimal pyqual usage."""
from pyqual import Pipeline, PyqualConfig

Pipeline(PyqualConfig.load("pyqual.yaml")).run()
