import subprocess
import time
from pathlib import Path
from pyqual.bulk.models import ProjectRunState, RunStatus
from pyqual.bulk.parser import _parse_stage_start, _parse_iteration_header, _parse_output_line
from pyqual.constants import ERROR_MSG_MAX_CHARS

def _run_single_project(state: ProjectRunState, dry_run: bool = False, timeout: int = 0, pyqual_cmd: str = "pyqual", log_dir: Path | None = None, analyze: bool = False) -> None:
    state.status = RunStatus.RUNNING
    state.start_time = time.monotonic()
    config_path = state.path / "pyqual.yaml"
    if not config_path.exists():
        state.status = RunStatus.SKIPPED
        state.error_msg = "no pyqual.yaml"
        return
    cmd = [pyqual_cmd, "run", "--config", str(config_path), "--workdir", str(state.path)]
    if dry_run: cmd.append("--dry-run")
    log_fh = (log_dir / f"{state.name}.log").open("w") if log_dir else None
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=str(state.path))
        for line in proc.stdout:
            if log_fh: log_fh.write(line)
            _parse_output_line(state, line)
        proc.wait(timeout=timeout if timeout > 0 else None)
        state.duration = time.monotonic() - state.start_time
        if state.status == RunStatus.RUNNING:
            state.status = RunStatus.PASSED if proc.returncode == 0 else RunStatus.FAILED
    except Exception as exc:
        state.status = RunStatus.ERROR
        state.error_msg = str(exc)[:ERROR_MSG_MAX_CHARS]
    finally:
        if log_fh: log_fh.close()