"""Error taxonomy and runtime failure classification.

Standardized error codes and pattern-based classification of stage failures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Final


class ErrorDomain(str, Enum):
    CONFIG   = "CONFIG"    # pyqual.yaml is wrong
    ENV      = "ENV"       # missing binary / API key / network
    PROJECT  = "PROJECT"   # project code issue (test / lint / gate failure)
    PIPELINE = "PIPELINE"  # subprocess timeout / I/O crash
    LLM      = "LLM"       # LLM / fix-stage problem
    RELEASE  = "RELEASE"   # release-state (git / registry / version) preflight


# Full error codes  (domain_name : specific_name)
class EC:
    """Namespace for standardised error-code string constants."""
    # CONFIG
    CONFIG_NOT_FOUND        = "E_PYQUAL_CONFIG_NOT_FOUND"
    CONFIG_YAML_PARSE       = "E_PYQUAL_CONFIG_YAML_PARSE"
    CONFIG_YAML_EMPTY       = "E_PYQUAL_CONFIG_YAML_EMPTY"
    CONFIG_STAGE_NO_CMD     = "E_PYQUAL_CONFIG_STAGE_NO_CMD"
    CONFIG_STAGE_BOTH_CMDS  = "E_PYQUAL_CONFIG_STAGE_BOTH_CMDS"
    CONFIG_UNKNOWN_PRESET   = "E_PYQUAL_CONFIG_UNKNOWN_PRESET"
    CONFIG_BAD_ITERATIONS   = "E_PYQUAL_CONFIG_BAD_ITERATIONS"
    CONFIG_BAD_THRESHOLD    = "E_PYQUAL_CONFIG_BAD_THRESHOLD"
    CONFIG_UNKNOWN_ON_FAIL  = "E_PYQUAL_CONFIG_UNKNOWN_ON_FAIL"
    CONFIG_REGISTRY_ERROR   = "E_PYQUAL_CONFIG_REGISTRY_ERROR"
    # ENV
    ENV_TOOL_MISSING        = "E_PYQUAL_ENV_TOOL_MISSING"
    ENV_TOOL_MISSING_OPT    = "E_PYQUAL_ENV_TOOL_MISSING_OPT"
    ENV_API_KEY_MISSING     = "E_PYQUAL_ENV_API_KEY_MISSING"
    ENV_UNKNOWN_METRIC      = "E_PYQUAL_ENV_UNKNOWN_METRIC"
    ENV_NO_STAGES           = "E_PYQUAL_ENV_NO_STAGES"
    ENV_NO_GATES            = "E_PYQUAL_ENV_NO_GATES"
    # PROJECT
    PROJECT_TEST_FAILURE    = "E_PYQUAL_PROJECT_TEST_FAILURE"
    PROJECT_LINT_FAILURE    = "E_PYQUAL_PROJECT_LINT_FAILURE"
    PROJECT_GATE_FAILURE    = "E_PYQUAL_PROJECT_GATE_FAILURE"
    PROJECT_BUILD_FAILURE   = "E_PYQUAL_PROJECT_BUILD_FAILURE"
    PROJECT_GENERIC         = "E_PYQUAL_PROJECT_GENERIC"
    # PIPELINE
    PIPELINE_TIMEOUT        = "E_PYQUAL_PIPELINE_TIMEOUT"
    PIPELINE_IO_ERROR       = "E_PYQUAL_PIPELINE_IO_ERROR"
    PIPELINE_CMD_NOT_FOUND  = "E_PYQUAL_PIPELINE_CMD_NOT_FOUND"
    PIPELINE_GENERIC        = "E_PYQUAL_PIPELINE_GENERIC"
    # LLM
    LLM_API_KEY_MISSING     = "E_PYQUAL_LLM_API_KEY_MISSING"
    LLM_NETWORK_ERROR       = "E_PYQUAL_LLM_NETWORK_ERROR"
    LLM_FIX_FAILED          = "E_PYQUAL_LLM_FIX_FAILED"
    LLM_GENERIC             = "E_PYQUAL_LLM_GENERIC"
    # RELEASE (preflight release-state validation)
    RELEASE_GIT_NOT_REPO      = "E_PYQUAL_RELEASE_GIT_NOT_REPO"
    RELEASE_GIT_DIRTY         = "E_PYQUAL_RELEASE_GIT_DIRTY"
    RELEASE_GIT_BEHIND        = "E_PYQUAL_RELEASE_GIT_BEHIND"
    RELEASE_METADATA_MISSING  = "E_PYQUAL_RELEASE_METADATA_MISSING"
    RELEASE_VERSION_MISMATCH  = "E_PYQUAL_RELEASE_VERSION_MISMATCH"
    RELEASE_MODULE_VERSION_MISMATCH = "E_PYQUAL_RELEASE_MODULE_VERSION_MISMATCH"
    RELEASE_INVALID_VERSION   = "E_PYQUAL_RELEASE_INVALID_VERSION"
    RELEASE_REGISTRY_UNSUPPORTED = "E_PYQUAL_RELEASE_REGISTRY_UNSUPPORTED"
    RELEASE_REGISTRY_UNAVAILABLE = "E_PYQUAL_RELEASE_REGISTRY_UNAVAILABLE"
    RELEASE_VERSION_EXISTS    = "E_PYQUAL_RELEASE_VERSION_EXISTS"


def error_domain(code: str) -> ErrorDomain | None:
    """Return the domain of a standardised error code string."""
    for domain in ErrorDomain:
        if code.startswith(f"E_PYQUAL_{domain.value}_"):
            return domain
    return None


class Severity(str, Enum):
    ERROR = "error"      # pipeline cannot start
    WARNING = "warning"  # pipeline may behave unexpectedly
    INFO = "info"        # suggestion


@dataclass
class StageFailure:
    """Runtime failure description from a completed stage."""
    stage_name: str
    returncode: int
    stderr: str
    stdout: str
    duration: float
    is_fix_stage: bool = False   # True when this IS the LLM fix stage
    timed_out: bool = False

    @property
    def error_code(self) -> str:
        """Classify failure into a standardised error code."""
        return _classify_failure(self)

    @property
    def domain(self) -> ErrorDomain | None:
        return error_domain(self.error_code)


# ---------------------------------------------------------------------------
# Runtime failure classifier
# ---------------------------------------------------------------------------

# Patterns that indicate environment / config problems (tool not installed, etc.)
_ENV_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"command not found", re.I),
    re.compile(r"No such file or directory", re.I),
    re.compile(r"not found on PATH", re.I),
    re.compile(r"ModuleNotFoundError", re.I),
    re.compile(r"ImportError", re.I),
    re.compile(r"Permission denied", re.I),
    re.compile(r"OPENROUTER_API_KEY", re.I),
    re.compile(r"API key", re.I),
    re.compile(r"AuthenticationError", re.I),
]

_LLM_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"openrouter", re.I),
    re.compile(r"litellm", re.I),
    re.compile(r"anthropic|openai|gemini", re.I),
    re.compile(r"rate.limit", re.I),
    re.compile(r"context.length", re.I),
    re.compile(r"llx.*error|error.*llx", re.I),
]

_TEST_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"FAILED\s+tests/", re.I),
    re.compile(r"pytest.*failed", re.I),
    re.compile(r"\d+ failed", re.I),
    re.compile(r"AssertionError", re.I),
    re.compile(r"ERRORS?\s+collecting", re.I),
]

_LINT_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"ruff.*error|error.*ruff", re.I),
    re.compile(r"pylint.*error|flake8.*error", re.I),
    re.compile(r"E\d{3,4}|W\d{3,4}|F\d{3,4}", re.I),
]


def _match_env_subtype(combined: str) -> str:
    """Distinguish API-key vs network vs generic env failures."""
    upper = combined.upper()
    if "API" in upper or "KEY" in upper:
        return EC.ENV_API_KEY_MISSING
    return EC.ENV_TOOL_MISSING


def _match_fix_env_subtype(combined: str) -> str:
    """Distinguish fix-stage env failure subtypes."""
    upper = combined.upper()
    lower = combined.lower()
    if "API" in upper or "KEY" in upper:
        return EC.LLM_API_KEY_MISSING
    if "network" in lower or "connect" in lower:
        return EC.LLM_NETWORK_ERROR
    return EC.LLM_FIX_FAILED


# Ordered (pattern_list, error_code) pairs for general failure classification.
_GENERAL_CLASSIFIERS: Final[list[tuple[list[re.Pattern[str]], str]]] = [
    (_ENV_PATTERNS, "ENV"),
    (_LLM_PATTERNS, EC.LLM_GENERIC),
    (_TEST_PATTERNS, EC.PROJECT_TEST_FAILURE),
    (_LINT_PATTERNS, EC.PROJECT_LINT_FAILURE),
]


def _classify_failure(f: StageFailure) -> str:
    """Classify a stage failure into a standardized error code."""
    if f.timed_out:
        return EC.PIPELINE_TIMEOUT

    combined = f"{f.stderr}\n{f.stdout}".strip()

    # LLM fix stage failures are their own domain
    if f.is_fix_stage:
        for pat in _ENV_PATTERNS:
            if pat.search(combined):
                return _match_fix_env_subtype(combined)
        return EC.LLM_FIX_FAILED

    # No output at all — binary likely missing
    if not combined and f.returncode != 0:
        return EC.ENV_TOOL_MISSING

    for patterns, code in _GENERAL_CLASSIFIERS:
        for pat in patterns:
            if pat.search(combined):
                return _match_env_subtype(combined) if code == "ENV" else code

    return EC.PROJECT_GENERIC


__all__ = [
    "EC",
    "ErrorDomain",
    "Severity",
    "StageFailure",
    "error_domain",
    "_classify_failure",
]
