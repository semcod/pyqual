"""Planfile-backed ticket sync helpers for TODO.md and GitHub."""

import shutil
import subprocess
from pathlib import Path

PLANFILE_MARKDOWN_SOURCE = "markdown"
PLANFILE_GITHUB_SOURCE = "github"
PLANFILE_TODO_SOURCE = "todo"


def _load_sync_integration():
    """Try to load planfile integration, return None if not available."""
    try:
        from planfile.cli.cmd.cmd_sync import sync_integration
        return sync_integration
    except ImportError:
        return None


def _normalize_sources(source: str) -> list[str]:
    normalized = source.lower()
    if normalized == PLANFILE_TODO_SOURCE:
        return [PLANFILE_MARKDOWN_SOURCE]
    if normalized in {PLANFILE_MARKDOWN_SOURCE, PLANFILE_GITHUB_SOURCE}:
        return [normalized]
    if normalized == "all":
        return [PLANFILE_MARKDOWN_SOURCE, PLANFILE_GITHUB_SOURCE]
    raise ValueError(f"Unknown ticket source: {source}")


def sync_planfile_tickets(
    source: str,
    workdir: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync tickets via planfile backends."""
    sync_integration = _load_sync_integration()
    for index, integration_name in enumerate(_normalize_sources(source)):
        if sync_integration:
            sync_integration(
                integration_name,
                str(workdir),
                dry_run,
                direction,
                show_header=index == 0,
            )
        else:
            # Fallback to shelling out to planfile CLI (e.g. if installed via pipx)
            planfile_bin = shutil.which("planfile")
            if not planfile_bin:
                raise RuntimeError(
                    "Neither planfile python package nor planfile binary found. "
                    "Please install planfile to enable ticket syncing."
                )
            
            cmd = [planfile_bin, "sync", integration_name, str(workdir)]
            cmd.extend(["--direction", direction])
            if dry_run:
                cmd.append("--dry-run")
            
            # Print standard echo just like pyqual does
            if index == 0:
                print(f"🔄 Syncing via planfile CLI ({integration_name})...")
                
            subprocess.run(cmd, check=True)


def sync_todo_tickets(
    workdir: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync TODO.md tickets through planfile's markdown backend."""
    sync_planfile_tickets("todo", workdir=workdir, dry_run=dry_run, direction=direction)


def sync_github_tickets(
    workdir: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync GitHub issues through planfile's GitHub backend."""
    sync_planfile_tickets("github", workdir=workdir, dry_run=dry_run, direction=direction)


def sync_all_tickets(
    workdir: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync TODO.md and GitHub tickets through planfile."""
    sync_planfile_tickets("all", workdir=workdir, dry_run=dry_run, direction=direction)


def sync_from_gates(
    workdir: Path = Path("."),
    dry_run: bool = False,
    backends: list[str] | None = None,
) -> dict:
    """Check gates and sync tickets only if gates fail.

    This is what pyqual does internally when `on_fail: create_ticket` is set.
    Use this for programmatic gate-based ticket creation.

    Args:
        workdir: Project directory containing pyqual.yaml
        dry_run: Preview without making changes
        backends: List of backends to sync (default: ["markdown"])

    Returns:
        dict with {synced: bool, failures: list[str], backends: list[str]}
    """
    from pyqual.config import PyqualConfig
    from pyqual.gates import GateSet

    config_path = workdir / "pyqual.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"pyqual.yaml not found in {workdir}")

    config = PyqualConfig.load(config_path)
    gate_set = GateSet(config.gates)
    results = gate_set.check_all(workdir)

    failures = [r for r in results if not r.passed]

    if not failures:
        return {"synced": False, "failures": [], "backends": [], "all_passed": True}

    backends = backends or ["markdown"]

    if "all" in backends:
        sync_all_tickets(workdir=workdir, dry_run=dry_run, direction="from")
    else:
        for backend in backends:
            sync_planfile_tickets(backend, workdir=workdir, dry_run=dry_run, direction="from")

    return {
        "synced": True,
        "failures": [f.metric for f in failures],
        "backends": backends,
        "all_passed": False,
    }


def create_planfile_tickets_from_ruff(workdir: Path = Path("."), max_items: int = 5) -> int:
    """Extract ruff issues and directly execute 'planfile ticket create' for each.
    
    This delivers direct-to-storage persistence bypasses intermediate format drift.
    """
    import json
    import subprocess
    import shutil
    
    ruff_path = workdir / ".pyqual" / "ruff.json"
    if not ruff_path.exists():
        ruff_path = workdir / "ruff.json"
    if not ruff_path.exists():
        return 0
        
    planfile_bin = shutil.which("planfile")
    if not planfile_bin:
        return 0

    try:
        with open(ruff_path) as f:
            data = json.load(f)
    except Exception:
        return 0
        
    if not isinstance(data, list) or not data:
        return 0
        
    # Sort and limit
    data.sort(key=lambda x: (x.get("filename", ""), x.get("location", {}).get("row", 0)))
    
    count = 0
    seen = set()
    
    # Get existing ticket names to prevent duplicates (simple check)
    try:
        list_proc = subprocess.run(
            [planfile_bin, "ticket", "list", "--format", "json"], 
            capture_output=True, text=True, cwd=str(workdir)
        )
        existing_titles = ""
        if list_proc.returncode == 0:
            existing_titles = list_proc.stdout.lower()
    except Exception:
        existing_titles = ""

    for violation in data:
        if count >= max_items:
            break
            
        filename = violation.get("filename", "unknown")
        code = violation.get("code", "LINT")
        msg = violation.get("message", "Lint failure")
        line = violation.get("location", {}).get("row", "?")
        
        key = f"{filename}:{code}"
        if key in seen:
            continue
        seen.add(key)
        
        # Build descriptive title
        basename = filename.split("/")[-1]
        title = f"Fix {code} in {basename}"
        
        if title.lower() in existing_titles:
            continue
            
        description = f"{msg} at {filename}:{line}"
        
        # Try to create using Python API to enrich with autonomous executor properties
        created_via_api = False
        try:
            from planfile import Planfile
            from planfile.core.models.ticket import TicketExecutor, TicketExecution
            
            pf = Planfile(project_path=str(workdir))
            # Define fully-autonomous executor to fix without any manual interaction!
            auto_executor = TicketExecutor(
                kind="shell", 
                mode="automatic", 
                handler=f".venv/bin/ruff check --fix {filename}"
            )
            # Mark as immediately ready for queue processor
            auto_execution = TicketExecution(state="ready")
            
            pf.create_ticket(
                name=title,
                description=description,
                source={"tool": "pyqual"},
                labels=["ruff", "auto-generated", "autonomous"],
                files=[filename],
                executor=auto_executor,
                execution=auto_execution
            )
            created_via_api = True
            count += 1
        except ImportError:
            pass # Fallback to CLI below
        except Exception:
            pass # Fallback to CLI below

        if not created_via_api:
            cmd = [
                planfile_bin, "ticket", "create", title,
                "--label", "ruff",
                "--label", "auto-generated",
                "--description", description,
                "--source", "pyqual",
                "--files", filename
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True, cwd=str(workdir))
                count += 1
            except subprocess.CalledProcessError:
                pass
                
    return count
