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
BULK_ANALYSIS_MAX_CHARS = 80
BULK_STAGE_COLUMN_MIN_WIDTH = 12
BULK_STAGE_COLUMN_MAX_WIDTH = 20

# ---------------------------------------------------------------------------
# LLM / AI
# ---------------------------------------------------------------------------
DEFAULT_MAX_TOKENS = 2000
CONFIG_READ_MAX_CHARS = 2000
LLM_FIX_MAX_TOKENS = 1200       # for auto-fix config
LLM_HISTORY_MAX_TOKENS = 1500   # for history command

# ---------------------------------------------------------------------------
# CLI formatting
# ---------------------------------------------------------------------------
TIMESTAMP_COL_WIDTH = 19   # "YYYY-MM-DD HH:MM:SS"
TIMESTAMP_TIME_START = 11  # offset to skip "YYYY-MM-DD " prefix
BULK_PASS_PREVIEW = 20     # max passed-gate names to show inline
LOG_DETAIL_MAX_LEN = 80    # max chars for fallback log detail display
MODEL_COLUMN_WIDTH = 28  # width for model column in tables

# ---------------------------------------------------------------------------
# Default timeouts for profile stages
# ---------------------------------------------------------------------------
PREFACT_TIMEOUT = 900   # 15 minutes
FIX_TIMEOUT = 1800      # 30 minutes
# ---------------------------------------------------------------------------
DEFAULT_VALLM_PASS_MIN = 90   # default vallm pass percentage minimum
DEFAULT_COVERAGE_MIN = 80     # default test coverage minimum percentage

# ---------------------------------------------------------------------------
# Text truncation limits
# ---------------------------------------------------------------------------
TODO_HEAD_CHARS = 500          # chars to read from TODO.md header for parsing
STAGE_OUTPUT_MAX_CHARS = 200   # max chars for last meaningful output line
ERROR_MSG_MAX_CHARS = 200      # max chars for error messages in bulk run
ERROR_MSG_PREVIEW_CHARS = 30   # max chars for error message preview

# ---------------------------------------------------------------------------
# Additional magic numbers from TODO cleanup
# ---------------------------------------------------------------------------
BULK_INIT_MAX_CHARS = 500      # from bulk_init.py:249
BULK_RUN_ERROR_LINES = 200     # from bulk_run.py:324
BULK_RUN_STATUS_INTERVAL = 30  # from bulk_run.py:383
BULK_RUN_TABLE_WIDTH = 50      # from bulk_run.py:431
REPORT_GATE_COVERAGE = 80      # from report.py:43
REPORT_GATE_VALLM = 90         # from report.py:44
REPORT_GATE_SECURITY = 80      # from report.py:47

# ---------------------------------------------------------------------------
# Badge thresholds for README badges (used by report.py)
# ---------------------------------------------------------------------------
BADGE_THRESHOLD_CC_LOW = 5.0       # CC threshold for low complexity (green)
BADGE_THRESHOLD_CC_MED = 10.0      # CC threshold for medium complexity (yellow)
BADGE_THRESHOLD_CC_HIGH = 15.0     # CC threshold for high complexity (orange)
BADGE_THRESHOLD_EXCELLENT = 90     # Excellent threshold percentage
BADGE_THRESHOLD_GOOD = 75          # Good threshold percentage
BADGE_THRESHOLD_PASS = 60          # Pass threshold percentage
BADGE_THRESHOLD_POOR = 40          # Poor threshold percentage
BADGE_THRESHOLD_WARN = 50          # Warning threshold percentage
