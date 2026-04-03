"""Git plugin for pyqual — handles repository operations as metrics collector.

This plugin provides git status, commit, and push operations with proper
error handling and push protection detection.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry


@PluginRegistry.register
class GitCollector(MetricCollector):
    """Git repository operations collector — status, commit, push with protection handling."""

    name = "git"
    metadata = PluginMetadata(
        name="git",
        description="Git operations: status, commit, push with secret scanning and push protection detection",
        version="1.1.0",
        tags=["git", "vcs", "repository", "push-protection", "secrets", "security"],
        config_example="""
metrics:
  git_uncommitted_files_max: 0      # No uncommitted changes before push
  git_unstaged_files_max: 0         # All changes should be staged
  git_secrets_found_max: 0          # No secrets allowed
  git_push_protection_errors_max: 0 # No push protection violations

stages:
  - name: git_scan
    run: pyqual git scan --json

  - name: git_status
    run: pyqual git status --json

  - name: git_commit
    run: pyqual git commit -m "feat: automated commit" --if-changed

  - name: git_preflight
    run: pyqual git push --dry-run --json

  - name: git_push
    run: pyqual git push --detect-protection --json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect git metrics from .pyqual/git_*.json artifacts."""
        result: dict[str, float] = {}

        # Git status metrics
        status_path = workdir / ".pyqual" / "git_status.json"
        if status_path.exists():
            try:
                data = json.loads(status_path.read_text())
                self._collect_status_metrics(result, data)
            except (json.JSONDecodeError, TypeError):
                pass

        # Git push metrics
        push_path = workdir / ".pyqual" / "git_push.json"
        if push_path.exists():
            try:
                data = json.loads(push_path.read_text())
                self._collect_push_metrics(result, data)
            except (json.JSONDecodeError, TypeError):
                pass

        # Git commit metrics
        commit_path = workdir / ".pyqual" / "git_commit.json"
        if commit_path.exists():
            try:
                data = json.loads(commit_path.read_text())
                self._collect_commit_metrics(result, data)
            except (json.JSONDecodeError, TypeError):
                pass

        # Git scan metrics (secrets)
        scan_path = workdir / ".pyqual" / "git_scan.json"
        if scan_path.exists():
            try:
                data = json.loads(scan_path.read_text())
                self._collect_scan_metrics(result, data)
            except (json.JSONDecodeError, TypeError):
                pass

        # Pre-flight check metrics
        preflight_path = workdir / ".pyqual" / "git_preflight.json"
        if preflight_path.exists():
            try:
                data = json.loads(preflight_path.read_text())
                self._collect_preflight_metrics(result, data)
            except (json.JSONDecodeError, TypeError):
                pass

        return result

    def _collect_scan_metrics(self, result: dict[str, float], data: dict[str, Any]) -> None:
        """Extract metrics from secret scan results."""
        secrets = data.get("secrets_found", [])
        if isinstance(secrets, list):
            result["git_secrets_found"] = float(len(secrets))
            
            # Count by severity
            critical = len([s for s in secrets if s.get("severity") == "CRITICAL"])
            high = len([s for s in secrets if s.get("severity") == "HIGH"])
            medium = len([s for s in secrets if s.get("severity") == "MEDIUM"])
            low = len([s for s in secrets if s.get("severity") == "LOW"])
            
            result["git_secrets_critical"] = float(critical)
            result["git_secrets_high"] = float(high)
            result["git_secrets_medium"] = float(medium)
            result["git_secrets_low"] = float(low)
        
        # Scanners used
        scanners = data.get("scanners_used", [])
        if isinstance(scanners, list):
            result["git_scanners_used"] = float(len(scanners))
        
        # Files scanned
        files_scanned = data.get("total_files_scanned", 0)
        if files_scanned is not None:
            result["git_files_scanned"] = float(files_scanned)
        
        # Success (no secrets found)
        success = data.get("success", True)
        result["git_scan_success"] = 1.0 if success else 0.0

    def _collect_preflight_metrics(self, result: dict[str, float], data: dict[str, Any]) -> None:
        """Extract metrics from pre-flight check results."""
        can_push = data.get("can_push", True)
        result["git_preflight_can_push"] = 1.0 if can_push else 0.0
        
        # Blockers and warnings
        blockers = data.get("blockers", [])
        warnings = data.get("warnings", [])
        
        if isinstance(blockers, list):
            result["git_preflight_blockers"] = float(len(blockers))
        if isinstance(warnings, list):
            result["git_preflight_warnings"] = float(len(warnings))
        
        # Secrets scan from preflight
        secrets_scan = data.get("secrets_scan", {})
        if secrets_scan:
            secrets = secrets_scan.get("secrets_found", [])
            if isinstance(secrets, list):
                result["git_preflight_secrets_found"] = float(len(secrets))

    def _collect_status_metrics(self, result: dict[str, float], data: dict[str, Any]) -> None:
        """Extract metrics from git status output."""
        # Count uncommitted files
        uncommitted = data.get("uncommitted_files", [])
        if isinstance(uncommitted, list):
            result["git_uncommitted_files"] = float(len(uncommitted))

        # Count unstaged files
        unstaged = data.get("unstaged_files", [])
        if isinstance(unstaged, list):
            result["git_unstaged_files"] = float(len(unstaged))

        # Count staged files
        staged = data.get("staged_files", [])
        if isinstance(staged, list):
            result["git_staged_files"] = float(len(staged))

        # Count untracked files
        untracked = data.get("untracked_files", [])
        if isinstance(untracked, list):
            result["git_untracked_files"] = float(len(untracked))

        # Branch ahead/behind
        ahead = data.get("ahead", 0)
        if ahead is not None:
            result["git_commits_ahead"] = float(ahead)

        behind = data.get("behind", 0)
        if behind is not None:
            result["git_commits_behind"] = float(behind)

        # Is clean working directory
        is_clean = data.get("is_clean", False)
        result["git_is_clean"] = 1.0 if is_clean else 0.0

    def _collect_push_metrics(self, result: dict[str, float], data: dict[str, Any]) -> None:
        """Extract metrics from git push output."""
        success = data.get("success", False)
        result["git_push_success"] = 1.0 if success else 0.0

        # Push protection detection
        push_protected = data.get("push_protection_violation", False)
        result["git_push_protection_violation"] = 1.0 if push_protected else 0.0

        # Error count
        errors = data.get("errors", [])
        if isinstance(errors, list):
            result["git_push_errors"] = float(len(errors))

        # Commits pushed
        commits = data.get("commits_pushed", 0)
        if commits is not None:
            result["git_commits_pushed"] = float(commits)

    def _collect_commit_metrics(self, result: dict[str, float], data: dict[str, Any]) -> None:
        """Extract metrics from git commit output."""
        success = data.get("success", False)
        result["git_commit_success"] = 1.0 if success else 0.0

        # Files committed
        files = data.get("files_committed", [])
        if isinstance(files, list):
            result["git_files_committed"] = float(len(files))

        # Commit created
        commit_hash = data.get("commit_hash")
        result["git_commit_created"] = 1.0 if commit_hash else 0.0

    def get_config_example(self) -> str:
        """Return a ready-to-use YAML snippet for git operations."""
        return self.metadata.config_example


def run_git_command(
    args: list[str],
    cwd: Path | None = None,
    check: bool = False,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """Run a git command with proper error handling."""
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=check,
        )
        return result
    except subprocess.CalledProcessError as e:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=e.returncode,
            stdout=e.stdout if e.stdout else "",
            stderr=e.stderr if e.stderr else "",
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=127,
            stdout="",
            stderr="git command not found",
        )


def git_status(cwd: Path | None = None) -> dict[str, Any]:
    """Get git repository status.

    Returns dict with:
    - is_clean: bool
    - staged_files: list[str]
    - unstaged_files: list[str]
    - untracked_files: list[str]
    - uncommitted_files: list[str] (staged + unstaged)
    - branch: str
    - ahead: int
    - behind: int
    """
    result = {
        "is_clean": True,
        "staged_files": [],
        "unstaged_files": [],
        "untracked_files": [],
        "uncommitted_files": [],
        "branch": "",
        "ahead": 0,
        "behind": 0,
        "success": False,
        "error": None,
    }

    # Check if git repo
    git_check = run_git_command(["rev-parse", "--git-dir"], cwd=cwd)
    if git_check.returncode != 0:
        result["error"] = "Not a git repository"
        return result

    # Get status in porcelain format
    status_result = run_git_command(["status", "--porcelain", "-b"], cwd=cwd)
    if status_result.returncode != 0:
        result["error"] = status_result.stderr.strip()
        return result

    lines = status_result.stdout.strip().split("\n")
    staged = []
    unstaged = []
    untracked = []

    for line in lines:
        if not line:
            continue

        # Branch info line
        if line.startswith("##"):
            branch_info = line[3:].strip()
            # Parse branch and ahead/behind
            if "..." in branch_info:
                branch_part = branch_info.split("...")[0]
                result["branch"] = branch_part

                # Check for ahead/behind
                if "[" in branch_info:
                    ahead_behind = branch_info[branch_info.find("[") + 1 : branch_info.find("]")]
                    if "ahead" in ahead_behind:
                        ahead_match = re.search(r"ahead\s+(\d+)", ahead_behind)
                        if ahead_match:
                            result["ahead"] = int(ahead_match.group(1))
                    if "behind" in ahead_behind:
                        behind_match = re.search(r"behind\s+(\d+)", ahead_behind)
                        if behind_match:
                            result["behind"] = int(behind_match.group(1))
            else:
                result["branch"] = branch_info
            continue

        # File status (2 char status code + filename)
        if len(line) >= 3:
            status_code = line[:2]
            filename = line[3:]

            # Staged changes (first char is not space or ?)
            if status_code[0] not in " ?!":
                staged.append(filename)
            # Unstaged changes (second char is not space)
            elif status_code[1] != " ":
                unstaged.append(filename)
            # Untracked
            elif status_code == "??":
                untracked.append(filename)

    result["staged_files"] = staged
    result["unstaged_files"] = unstaged
    result["untracked_files"] = untracked
    result["uncommitted_files"] = staged + unstaged
    result["is_clean"] = not (staged or unstaged or untracked)
    result["success"] = True

    return result


def git_commit(
    message: str,
    cwd: Path | None = None,
    add_all: bool = False,
    only_if_changed: bool = False,
) -> dict[str, Any]:
    """Create a git commit.

    Args:
        message: Commit message
        cwd: Working directory
        add_all: Run git add -A before commit
        only_if_changed: Only commit if there are changes

    Returns dict with:
    - success: bool
    - commit_hash: str | None
    - files_committed: list[str]
    - skipped: bool (if only_if_changed and no changes)
    - error: str | None
    """
    result = {
        "success": False,
        "commit_hash": None,
        "files_committed": [],
        "skipped": False,
        "error": None,
    }

    # Check if git repo
    git_check = run_git_command(["rev-parse", "--git-dir"], cwd=cwd)
    if git_check.returncode != 0:
        result["error"] = "Not a git repository"
        return result

    # Get status first
    status = git_status(cwd)
    if not status["success"]:
        result["error"] = status.get("error", "Failed to get status")
        return result

    # Check if we should skip (no changes and only_if_changed)
    if only_if_changed and status["is_clean"]:
        result["skipped"] = True
        result["success"] = True
        return result

    # Add all if requested
    if add_all:
        add_result = run_git_command(["add", "-A"], cwd=cwd)
        if add_result.returncode != 0:
            result["error"] = f"git add failed: {add_result.stderr}"
            return result
        # Refresh status
        status = git_status(cwd)

    # Check if there are staged changes to commit
    if not status["staged_files"] and not add_all:
        if only_if_changed:
            result["skipped"] = True
            result["success"] = True
            return result
        result["error"] = "No staged changes to commit"
        return result

    # Create commit
    commit_result = run_git_command(["commit", "-m", message], cwd=cwd)
    if commit_result.returncode != 0:
        result["error"] = commit_result.stderr.strip()
        return result

    # Get commit hash
    hash_result = run_git_command(["rev-parse", "HEAD"], cwd=cwd)
    if hash_result.returncode == 0:
        result["commit_hash"] = hash_result.stdout.strip()

    result["files_committed"] = status["staged_files"]
    result["success"] = True

    return result


def git_push(
    cwd: Path | None = None,
    remote: str = "origin",
    branch: str | None = None,
    force: bool = False,
    force_with_lease: bool = False,
) -> dict[str, Any]:
    """Push commits to remote.

    Args:
        cwd: Working directory
        remote: Remote name (default: origin)
        branch: Branch name (default: current branch)
        force: Force push
        force_with_lease: Force push with lease (safer)

    Returns dict with:
    - success: bool
    - commits_pushed: int
    - push_protection_violation: bool
    - errors: list[str]
    - output: str
    """
    result = {
        "success": False,
        "commits_pushed": 0,
        "push_protection_violation": False,
        "errors": [],
        "output": "",
    }

    # Check if git repo
    git_check = run_git_command(["rev-parse", "--git-dir"], cwd=cwd)
    if git_check.returncode != 0:
        result["errors"].append("Not a git repository")
        return result

    # Get current branch if not specified
    if branch is None:
        branch_result = run_git_command(["branch", "--show-current"], cwd=cwd)
        if branch_result.returncode == 0:
            branch = branch_result.stdout.strip()
        else:
            result["errors"].append("Could not determine current branch")
            return result

    # Build push command
    push_args = ["push", remote, branch]
    if force_with_lease:
        push_args.insert(2, "--force-with-lease")
    elif force:
        push_args.insert(2, "--force")

    push_result = run_git_command(push_args, cwd=cwd, check=False)

    result["output"] = push_result.stdout + push_result.stderr

    # Detect push protection
    output_lower = result["output"].lower()
    if "push protection" in output_lower or "gh013" in output_lower:
        result["push_protection_violation"] = True
        result["errors"].append("GitHub Push Protection violation detected")

    # Check for other errors
    if push_result.returncode != 0:
        # Extract error messages
        stderr_lines = push_result.stderr.strip().split("\n")
        for line in stderr_lines:
            line = line.strip()
            if line and not line.startswith("remote: "):
                result["errors"].append(line)
            elif "error:" in line.lower():
                result["errors"].append(line.replace("remote: ", ""))

    # Count commits pushed (check if already up to date)
    if "everything up-to-date" in result["output"].lower():
        result["commits_pushed"] = 0
        result["success"] = True
    elif push_result.returncode == 0:
        # Try to count commits
        count_result = run_git_command(
            ["rev-list", "--count", f"{remote}/{branch}..{branch}"],
            cwd=cwd,
        )
        if count_result.returncode == 0:
            try:
                result["commits_pushed"] = int(count_result.stdout.strip())
            except ValueError:
                pass
        result["success"] = True

    return result


def git_add(paths: list[str] | str, cwd: Path | None = None) -> dict[str, Any]:
    """Stage files for commit.

    Args:
        paths: File path(s) to stage, or "-A" for all
        cwd: Working directory

    Returns dict with:
    - success: bool
    - files_added: list[str]
    - error: str | None
    """
    result = {
        "success": False,
        "files_added": [],
        "error": None,
    }

    # Check if git repo
    git_check = run_git_command(["rev-parse", "--git-dir"], cwd=cwd)
    if git_check.returncode != 0:
        result["error"] = "Not a git repository"
        return result

    # Build add command
    if isinstance(paths, str):
        paths = [paths]

    add_args = ["add"] + paths
    add_result = run_git_command(add_args, cwd=cwd)

    if add_result.returncode != 0:
        result["error"] = add_result.stderr.strip()
        return result

    # Get list of staged files
    status = git_status(cwd)
    result["files_added"] = status.get("staged_files", [])
    result["success"] = True

    return result


# =============================================================================
# SECRET SCANNING - Pre-flight checks before push
# =============================================================================

# Common secret patterns (provider-specific)
SECRET_PATTERNS = {
    # GitHub
    "github_token": re.compile(
        r"gh[pousr]_[A-Za-z0-9_]{36,}|github_pat_[A-Za-z0-9_]{22,}|ghu_[A-Za-z0-9]{36}"
    ),
    "github_oauth": re.compile(r"[0-9a-f]{40}"),  # Legacy OAuth
    
    # AWS
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "aws_secret_key": re.compile(r"[0-9a-zA-Z/+]{40}"),
    "aws_session_token": re.compile(r"FwoGZXIvYXdzE[A-Za-z0-9/+=]{100,}"),
    
    # Generic API Keys
    "api_key_generic": re.compile(
        r"api[_-]?key[\s]*[=:]+[\s]*['\"]?[a-z0-9]{32,}['\"]?",
        re.IGNORECASE,
    ),
    "api_secret_generic": re.compile(
        r"api[_-]?secret[\s]*[=:]+[\s]*['\"]?[a-z0-9]{32,}['\"]?",
        re.IGNORECASE,
    ),
    
    # Private Keys
    "private_key": re.compile(
        r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "ssh_key": re.compile(r"ssh-(rsa|dss|ed25519) [A-Za-z0-9+/]{200,}"),
    
    # Database URLs with credentials
    "postgres_url": re.compile(
        r"postgres(ql)?://[^:]+:[^@]+@[^/]+",
        re.IGNORECASE,
    ),
    "mysql_url": re.compile(
        r"mysql://[^:]+:[^@]+@[^/]+",
        re.IGNORECASE,
    ),
    "mongodb_url": re.compile(
        r"mongodb(\+srv)?://[^:]+:[^@]+@[^/]+",
        re.IGNORECASE,
    ),
    
    # JWT Tokens
    "jwt_token": re.compile(r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*"),
    
    # Slack
    "slack_token": re.compile(r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*"),
    
    # Stripe
    "stripe_key": re.compile(r"sk_live_[0-9a-zA-Z]{24,}"),
    "stripe_test_key": re.compile(r"sk_test_[0-9a-zA-Z]{24,}"),
    
    # Generic high-entropy strings (potential secrets)
    "high_entropy": re.compile(r"[a-zA-Z0-9_\-]{40,}"),
}


def scan_for_secrets(
    paths: list[str] | None = None,
    cwd: Path | None = None,
    use_trufflehog: bool = True,
    use_gitleaks: bool = True,
    use_patterns: bool = True,
) -> dict[str, Any]:
    """Scan for secrets in files before push.

    Args:
        paths: Files to scan (default: staged files)
        cwd: Working directory
        use_trufflehog: Use trufflehog if available
        use_gitleaks: Use gitleaks if available
        use_patterns: Use built-in regex patterns

    Returns dict with:
    - success: bool (True if no secrets found)
    - secrets_found: list[dict] - List of found secrets with details
    - scanners_used: list[str] - Which scanners were used
    - total_files_scanned: int
    - error: str | None
    """
    result = {
        "success": True,
        "secrets_found": [],
        "scanners_used": [],
        "total_files_scanned": 0,
        "error": None,
    }

    # Get files to scan
    if paths is None:
        status = git_status(cwd)
        if not status["success"]:
            result["error"] = status.get("error", "Failed to get git status")
            return result
        paths = status.get("staged_files", []) + status.get("unstaged_files", [])
    
    if not paths:
        return result  # No files to scan

    result["total_files_scanned"] = len(paths)
    workdir = cwd or Path(".")

    # Try trufflehog first (most comprehensive)
    if use_trufflehog and shutil.which("trufflehog"):
        result["scanners_used"].append("trufflehog")
        th_result = _scan_with_trufflehog(paths, workdir)
        result["secrets_found"].extend(th_result.get("findings", []))

    # Try gitleaks
    if use_gitleaks and shutil.which("gitleaks"):
        result["scanners_used"].append("gitleaks")
        gl_result = _scan_with_gitleaks(paths, workdir)
        result["secrets_found"].extend(gl_result.get("findings", []))

    # Fallback to built-in patterns
    if use_patterns and not result["scanners_used"]:
        result["scanners_used"].append("builtin_patterns")
        pattern_result = _scan_with_patterns(paths, workdir)
        result["secrets_found"].extend(pattern_result.get("findings", []))

    # Additional pattern scan even if other scanners found something
    # (catches things they might miss)
    if use_patterns and result["scanners_used"]:
        pattern_result = _scan_with_patterns(paths, workdir)
        # Add only findings not already detected
        existing = {(s["file"], s["line"]) for s in result["secrets_found"]}
        for finding in pattern_result.get("findings", []):
            key = (finding["file"], finding["line"])
            if key not in existing:
                result["secrets_found"].append(finding)

    result["success"] = len(result["secrets_found"]) == 0
    return result


def _scan_with_trufflehog(paths: list[str], cwd: Path) -> dict[str, Any]:
    """Run trufflehog filesystem scan on specific paths."""
    result = {"findings": []}
    
    for path in paths:
        file_path = cwd / path
        if not file_path.exists():
            continue
            
        # Run trufflehog on single file
        cmd_result = run_git_command(
            ["trufflehog", "filesystem", "--json", str(file_path)],
            cwd=cwd,
            check=False,
        )
        
        if cmd_result.returncode != 0 and not cmd_result.stdout:
            continue
            
        # Parse JSON lines output
        for line in cmd_result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                finding = {
                    "file": path,
                    "line": data.get("SourceMetadata", {}).get("Data", {}).get("Filesystem", {}).get("line", 0),
                    "type": data.get("DetectorName", "unknown"),
                    "provider": data.get("DetectorName", "unknown"),
                    "raw": data.get("Raw", "")[:50] + "..." if len(data.get("Raw", "")) > 50 else data.get("Raw", ""),
                    "scanner": "trufflehog",
                    "severity": "HIGH" if data.get("Verified") else "MEDIUM",
                }
                result["findings"].append(finding)
            except json.JSONDecodeError:
                continue
    
    return result


def _scan_with_gitleaks(paths: list[str], cwd: Path) -> dict[str, Any]:
    """Run gitleaks detect on specific paths."""
    result = {"findings": []}
    
    for path in paths:
        file_path = cwd / path
        if not file_path.exists():
            continue
            
        # Run gitleaks on single file
        cmd_result = run_git_command(
            ["gitleaks", "detect", "--source", str(file_path), "--verbose", "--no-git"],
            cwd=cwd,
            check=False,
        )
        
        # gitleaks exits with error code when findings detected
        output = cmd_result.stdout + cmd_result.stderr
        
        # Parse findings from output
        for line in output.split("\n"):
            # Look for lines like: "Found: AWS Access Key..."
            if "Found:" in line:
                # Extract rule name and file info
                match = re.search(r"Found:\s+(.+?)\s+at\s+(.+?):(\d+)", line)
                if match:
                    rule_name, file_found, line_num = match.groups()
                    finding = {
                        "file": path,
                        "line": int(line_num) if line_num.isdigit() else 0,
                        "type": rule_name,
                        "provider": rule_name,
                        "raw": "",
                        "scanner": "gitleaks",
                        "severity": "HIGH",
                    }
                    result["findings"].append(finding)
    
    return result


def _scan_with_patterns(paths: list[str], cwd: Path) -> dict[str, Any]:
    """Scan files using built-in regex patterns."""
    result = {"findings": []}
    
    for path in paths:
        file_path = cwd / path
        if not file_path.exists():
            continue
            
        # Skip binary files
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except (IOError, OSError):
            continue
        
        lines = content.split("\n")
        
        for line_num, line in enumerate(lines, 1):
            for pattern_name, pattern in SECRET_PATTERNS.items():
                matches = pattern.findall(line)
                for match in matches:
                    # Skip obvious false positives
                    if _is_likely_false_positive(match, pattern_name, line):
                        continue
                    
                    finding = {
                        "file": path,
                        "line": line_num,
                        "type": pattern_name,
                        "provider": _get_provider_for_pattern(pattern_name),
                        "raw": match[:50] + "..." if len(match) > 50 else match,
                        "scanner": "builtin_patterns",
                        "severity": _get_severity_for_pattern(pattern_name),
                    }
                    result["findings"].append(finding)
    
    return result


def _is_likely_false_positive(match: str, pattern_name: str, line: str) -> bool:
    """Check if a match is likely a false positive."""
    # Skip placeholder/example values
    placeholders = [
        "example", "placeholder", "dummy", "fake", "test", "sample",
        "your_key_here", "xxx", "<", ">", "${", "{{", "{%",
    ]
    match_lower = match.lower()
    if any(p in match_lower for p in placeholders):
        return True
    
    # Skip hex color codes (40 chars looks like AWS secret but it's a color)
    if pattern_name == "aws_secret_key" and re.match(r"^[0-9a-fA-F]{40}$", match):
        # Check if it's in a CSS-like context
        if "color" in line.lower() or "background" in line.lower():
            return True
    
    # Skip hash values (SHA, MD5)
    if pattern_name == "high_entropy":
        # If surrounded by quotes and looks like a hash
        if re.match(r"^[0-9a-fA-F]{40}$", match):
            return True
    
    return False


def _get_provider_for_pattern(pattern_name: str) -> str:
    """Map pattern name to provider."""
    provider_map = {
        "github_token": "GitHub",
        "github_oauth": "GitHub",
        "aws_access_key": "AWS",
        "aws_secret_key": "AWS",
        "aws_session_token": "AWS",
        "api_key_generic": "Generic",
        "api_secret_generic": "Generic",
        "private_key": "Crypto",
        "ssh_key": "SSH",
        "postgres_url": "Database",
        "mysql_url": "Database",
        "mongodb_url": "Database",
        "jwt_token": "JWT",
        "slack_token": "Slack",
        "stripe_key": "Stripe",
        "stripe_test_key": "Stripe",
        "high_entropy": "Unknown",
    }
    return provider_map.get(pattern_name, "Unknown")


def _get_severity_for_pattern(pattern_name: str) -> str:
    """Get severity level for pattern type."""
    severity_map = {
        "github_token": "CRITICAL",
        "aws_access_key": "CRITICAL",
        "aws_secret_key": "CRITICAL",
        "private_key": "CRITICAL",
        "stripe_key": "CRITICAL",
        "api_key_generic": "HIGH",
        "api_secret_generic": "HIGH",
        "jwt_token": "HIGH",
        "slack_token": "HIGH",
        "postgres_url": "MEDIUM",
        "mysql_url": "MEDIUM",
        "mongodb_url": "MEDIUM",
        "high_entropy": "LOW",
    }
    return severity_map.get(pattern_name, "MEDIUM")


def preflight_push_check(
    cwd: Path | None = None,
    remote: str = "origin",
    branch: str | None = None,
    scan_secrets: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Pre-flight check before push - scan for secrets and validate.

    Args:
        cwd: Working directory
        remote: Remote name
        branch: Branch name (default: current)
        scan_secrets: Run secret scanning
        dry_run: Don't actually push, just validate

    Returns dict with:
    - can_push: bool
    - blockers: list[str] - Why push would fail
    - warnings: list[str] - Non-blocking issues
    - secrets_scan: dict - Secret scan results
    - dry_run: bool
    """
    result = {
        "can_push": True,
        "blockers": [],
        "warnings": [],
        "secrets_scan": {},
        "dry_run": dry_run,
    }

    workdir = cwd or Path(".")

    # Check git status
    status = git_status(workdir)
    if not status["success"]:
        result["can_push"] = False
        result["blockers"].append(f"Git error: {status.get('error')}")
        return result

    # Check for uncommitted changes
    if status["uncommitted_files"]:
        result["warnings"].append(
            f"You have {len(status['uncommitted_files'])} uncommitted file(s)"
        )

    # Check if ahead of remote
    if status["ahead"] == 0:
        result["blockers"].append("No commits to push (everything up to date)")
        result["can_push"] = False
        return result

    # Secret scanning
    if scan_secrets:
        scan_result = scan_for_secrets(cwd=workdir)
        result["secrets_scan"] = scan_result
        
        if not scan_result["success"]:
            result["can_push"] = False
            secrets = scan_result.get("secrets_found", [])
            critical = [s for s in secrets if s.get("severity") == "CRITICAL"]
            high = [s for s in secrets if s.get("severity") == "HIGH"]
            
            if critical:
                result["blockers"].append(
                    f"Found {len(critical)} CRITICAL secret(s) - push blocked"
                )
            if high:
                result["warnings"].append(
                    f"Found {len(high)} HIGH severity potential secret(s)"
                )
            
            # Show first few findings
            for finding in secrets[:5]:
                file = finding.get("file", "unknown")
                line = finding.get("line", 0)
                type_ = finding.get("type", "unknown")
                severity = finding.get("severity", "MEDIUM")
                msg = f"  [{severity}] {type_} in {file}:{line}"
                if severity == "CRITICAL":
                    result["blockers"].append(msg)
                else:
                    result["warnings"].append(msg)

    return result
