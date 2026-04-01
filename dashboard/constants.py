"""Dashboard API constants.

Centralized constants for the Pyqual Dashboard API to avoid magic numbers.
"""

# API Defaults
DEFAULT_RUNS_LIMIT = 50
"""Default number of recent runs to return."""

DEFAULT_METRIC_HISTORY_DAYS = 30
"""Default number of days for metric history queries."""

DEFAULT_STAGE_PERFORMANCE_DAYS = 30
"""Default number of days for stage performance queries."""

DEFAULT_GATE_STATUS_DAYS = 7
"""Default number of days for gate status queries."""

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
]
"""Allowed origins for CORS."""

# Security
DEFAULT_INGEST_TOKEN = "default-token-change-me"
"""Default token for ingest endpoint (should be overridden in production)."""

# Server Settings
DEFAULT_HOST = "0.0.0.0"
"""Default host for uvicorn server."""

DEFAULT_PORT = 8000
"""Default port for uvicorn server."""

# File Paths
PROJECTS_BASE_DIR = "projects"
"""Base directory for project data."""

PYQUAL_SUBDIR = ".pyqual"
"""Subdirectory for pyqual data within projects."""

PIPELINE_DB_NAME = "pipeline.db"
"""Name of the pipeline database file."""

SUMMARY_JSON_NAME = "summary.json"
"""Name of the summary JSON file."""

STATIC_DIR = "../dist"
"""Directory for static files (production build)."""

# HTTP Status
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
