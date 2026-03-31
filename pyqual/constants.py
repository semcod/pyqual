"""Shared constants for pyqual — extracted from various modules to avoid magic numbers."""

# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------
TIMEOUT_EXIT_CODE = 124
STDERR_TAIL_CHARS = 500
STDOUT_TAIL_CHARS = 2000
DEFAULT_STAGE_TIMEOUT = 300

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PYQUAL_DIR = ".pyqual"
PIPELINE_DB = ".pyqual/pipeline.db"
PIPELINE_TABLE = "pipeline_logs"
LLX_MCP_REPORT = ".pyqual/llx_mcp.json"
LLX_HISTORY_FILE = ".pyqual/llx_history.jsonl"

# ---------------------------------------------------------------------------
# CLI defaults
# ---------------------------------------------------------------------------
DEFAULT_MCP_PORT = 8000
STATUS_COLUMN_WIDTH = 12
MAX_DESCRIPTION_LENGTH = 50

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
DEFAULT_MAX_TOKENS = 2000
CONFIG_READ_MAX_CHARS = 2000

# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------
README_EXCERPT_MAX_CHARS = 300
TOP_LEVEL_FILES_MAX = 30
DEFAULT_CC_MAX = 15
BULK_LINE_TRUNCATE = 120
BULK_TABLE_PROJECT_MIN_WIDTH = 20
BULK_TABLE_PROJECT_MAX_WIDTH = 28
