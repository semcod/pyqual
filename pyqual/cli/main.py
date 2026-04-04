"""Shared CLI setup — app, console, logging configuration.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console

from pyqual.constants import TIMESTAMP_COL_WIDTH

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s — %(message)s"
_TIMESTAMP_COL_WIDTH = TIMESTAMP_COL_WIDTH  # "YYYY-MM-DD HH:MM:SS"

app = typer.Typer(help="Declarative quality gate loops for AI-assisted development.")
console = Console()
stderr_console = Console(stderr=True)

# Sub-apps
git_app = typer.Typer(help="Git repository operations: status, commit, push with protection handling.")
app.add_typer(git_app, name="git")

tickets_app = typer.Typer(help="Control planfile-backed tickets from TODO.md and GitHub.")
app.add_typer(tickets_app, name="tickets")


def setup_logging(verbose: bool, workdir: Path = Path(".")) -> None:
    """Configure Python logging for pyqual.pipeline.

    Always writes structured JSON lines to .pyqual/pipeline.log (handled by Pipeline).
    With --verbose, also prints human-readable lines to stderr.
    """
    logger = logging.getLogger("pyqual")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    if verbose:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S"))
        logger.addHandler(handler)
    else:
        logger.addHandler(logging.NullHandler())
