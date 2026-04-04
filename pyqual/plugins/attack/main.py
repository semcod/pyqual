"""Attack plugin for pyqual — aggressive merge automation and conflict resolution.

This plugin provides automatic merge capabilities with an "attack" strategy:
- Auto-merge PRs when all checks pass
- Aggressive conflict resolution preferring incoming changes
- Attack detection metrics for merge strategies
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry


@PluginRegistry.register
class AttackCollector(MetricCollector):
    """Attack merge collector — automerge with aggressive conflict resolution."""

    name = "attack"
    metadata = PluginMetadata(
        name="attack",
        description="Automerge with aggressive conflict resolution and attack detection metrics",
        version="1.0.0",
        tags=["git", "merge", "automerge", "attack", "conflict-resolution"],
        config_example="""
metrics:
  attack_merge_conflicts: 0       # Number of merge conflicts detected
  attack_auto_merges: 0           # Number of successful auto-merges
  attack_failed_merges: 0         # Number of failed merge attempts
  attack_strategy_used: "ours"     # Last used merge strategy

stages:
  - name: attack_check
    run: pyqual attack check --json

  - name: attack_merge
    run: pyqual attack merge --strategy=theirs --json
    when: metrics_pass
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect attack merge metrics from .pyqual/attack_*.json artifacts."""
        result: dict[str, float] = {}

        # Attack check metrics
        check_path = workdir / ".pyqual" / "attack_check.json"
        if check_path.exists():
            try:
                data = json.loads(check_path.read_text())
                self._collect_check_metrics(result, data)
            except (json.JSONDecodeError, TypeError):
                pass

        # Attack merge metrics
        merge_path = workdir / ".pyqual" / "attack_merge.json"
        if merge_path.exists():
            try:
                data = json.loads(merge_path.read_text())
                self._collect_merge_metrics(result, data)
            except (json.JSONDecodeError, TypeError):
                pass

        return result

    def _collect_check_metrics(self, result: dict[str, float], data: dict[str, Any]) -> None:
        """Extract metrics from attack check results."""
        result["attack_conflicts_detected"] = float(data.get("conflicts_detected", 0))
        result["attack_branches_behind"] = float(data.get("branches_behind", 0))
        result["attack_can_fast_forward"] = 1.0 if data.get("can_fast_forward", False) else 0.0
        result["attack_check_success"] = 1.0 if data.get("success", False) else 0.0

    def _collect_merge_metrics(self, result: dict[str, float], data: dict[str, Any]) -> None:
        """Extract metrics from attack merge results."""
        result["attack_merge_success"] = 1.0 if data.get("success", False) else 0.0
        result["attack_merge_conflicts_resolved"] = float(data.get("conflicts_resolved", 0))
        result["attack_merge_strategy_used"] = float(self._strategy_to_int(data.get("strategy", "none")))
        result["attack_merge_files_changed"] = float(data.get("files_changed", 0))

    @staticmethod
    def _strategy_to_int(strategy: str) -> int:
        """Convert strategy name to numeric value for metrics."""
        strategies = {"none": 0, "ours": 1, "theirs": 2, "union": 3}
        return strategies.get(strategy.lower(), 0)

    def get_config_example(self) -> str:
        """Return a ready-to-use YAML snippet for attack operations."""
        return self.metadata.config_example


def run_git_command(
    args: list[str],
    cwd: Path | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """Run a git command with proper error handling."""
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
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


def attack_check(cwd: Path | None = None) -> dict[str, Any]:
    """Check if attack merge is possible.

    Returns dict with:
    - conflicts_detected: int
    - branches_behind: int
    - can_fast_forward: bool
    - success: bool
    - error: str | None
    """
    result = {
        "conflicts_detected": 0,
        "branches_behind": 0,
        "can_fast_forward": False,
        "success": False,
        "error": None,
    }

    # Check if git repo
    git_check = run_git_command(["rev-parse", "--git-dir"], cwd=cwd)
    if git_check.returncode != 0:
        result["error"] = "Not a git repository"
        return result

    # Get current branch
    branch_result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if branch_result.returncode != 0:
        result["error"] = branch_result.stderr.strip()
        return result

    current_branch = branch_result.stdout.strip()

    # Check if behind main/master
    for main_branch in ["main", "master", "origin/main", "origin/master"]:
        behind_result = run_git_command(
            ["rev-list", "--count", f"{current_branch}..{main_branch}"],
            cwd=cwd,
        )
        if behind_result.returncode == 0:
            try:
                result["branches_behind"] = int(behind_result.stdout.strip())
                break
            except ValueError:
                pass

    # Check for merge conflicts by attempting a dry merge
    merge_check = run_git_command(
        ["merge-tree", "$(git merge-base HEAD origin/main)", "HEAD", "origin/main"],
        cwd=cwd,
    )
    if merge_check.returncode == 0:
        # Count conflict markers
        conflicts = merge_check.stdout.count("<<<<<<<")
        result["conflicts_detected"] = conflicts
        result["can_fast_forward"] = conflicts == 0

    result["success"] = True
    return result


def attack_merge(
    strategy: str = "theirs",
    cwd: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Perform attack merge with specified strategy.

    Args:
        strategy: "ours", "theirs", or "union"
        cwd: Working directory
        dry_run: If True, don't actually merge

    Returns dict with:
    - success: bool
    - conflicts_resolved: int
    - strategy: str
    - files_changed: int
    - error: str | None
    """
    result = {
        "success": False,
        "conflicts_resolved": 0,
        "strategy": strategy,
        "files_changed": 0,
        "error": None,
    }

    # Check if git repo
    git_check = run_git_command(["rev-parse", "--git-dir"], cwd=cwd)
    if git_check.returncode != 0:
        result["error"] = "Not a git repository"
        return result

    # Get current branch
    branch_result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if branch_result.returncode != 0:
        result["error"] = branch_result.stderr.strip()
        return result

    current_branch = branch_result.stdout.strip()

    # Fetch latest
    fetch_result = run_git_command(["fetch", "origin"], cwd=cwd)
    if fetch_result.returncode != 0:
        result["error"] = f"Fetch failed: {fetch_result.stderr}"
        return result

    if dry_run:
        # Check what would happen
        merge_check = run_git_command(
            ["merge-tree", "$(git merge-base HEAD origin/main)", "HEAD", "origin/main"],
            cwd=cwd,
        )
        if merge_check.returncode == 0:
            conflicts = merge_check.stdout.count("<<<<<<<")
            result["conflicts_resolved"] = conflicts
            result["files_changed"] = len([l for l in merge_check.stdout.split("\n") if l.startswith("changed")])
            result["success"] = True
        return result

    # Perform actual merge with strategy
    if strategy == "theirs":
        # Stash any changes
        run_git_command(["stash", "push", "-m", "attack_merge_stash"], cwd=cwd)

        # Try to merge
        merge_result = run_git_command(
            ["merge", "origin/main", "--no-commit", "--no-ff"],
            cwd=cwd,
        )

        if merge_result.returncode != 0:
            # Resolve conflicts by taking theirs
            run_git_command(["checkout", "--theirs", "."], cwd=cwd)
            run_git_command(["add", "."], cwd=cwd)

        # Get list of conflicted files
        status_result = run_git_command(["status", "--porcelain"], cwd=cwd)
        conflicts = [l[3:] for l in status_result.stdout.split("\n") if l.startswith("UU")]
        result["conflicts_resolved"] = len(conflicts)

        # Commit the merge
        commit_result = run_git_command(
            ["commit", "-m", f"chore: attack merge with {strategy} strategy [automated]"],
            cwd=cwd,
        )

        # Pop stash
        run_git_command(["stash", "pop"], cwd=cwd)

        if commit_result.returncode == 0:
            result["success"] = True
            # Count files changed
            diff_result = run_git_command(
                ["diff", "HEAD~1", "--name-only"],
                cwd=cwd,
            )
            result["files_changed"] = len([l for l in diff_result.stdout.split("\n") if l.strip()])

    return result


def auto_merge_pr(
    pr_number: int | None = None,
    branch: str | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Auto-merge a PR or branch when safe to do so.

    Args:
        pr_number: GitHub PR number (if using gh CLI)
        branch: Branch name to merge from
        cwd: Working directory

    Returns dict with:
    - success: bool
    - method: str (merge, squash, rebase)
    - error: str | None
    """
    result = {
        "success": False,
        "method": "none",
        "error": None,
    }

    # Check if gh CLI is available for PR operations
    gh_check = run_git_command(["--version"], cwd=cwd)  # Just check git
    if gh_check.returncode != 0:
        result["error"] = "Git not available"
        return result

    # Try to use gh CLI for PR merge
    gh_cli = run_git_command(["--version"], cwd=cwd)  # Placeholder

    if pr_number:
        # Use GitHub CLI if available
        gh_result = subprocess.run(
            ["gh", "pr", "merge", str(pr_number), "--auto", "--squash"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if gh_result.returncode == 0:
            result["success"] = True
            result["method"] = "squash"
        else:
            result["error"] = gh_result.stderr.strip()
    elif branch:
        # Manual merge of branch
        merge_result = attack_merge(strategy="theirs", cwd=cwd)
        if merge_result["success"]:
            result["success"] = True
            result["method"] = "attack_merge"
        else:
            result["error"] = merge_result.get("error", "Merge failed")
    else:
        result["error"] = "No PR number or branch specified"

    return result


# Merge strategy constants
MERGE_STRATEGIES = {
    "ours": "Prefer local changes",
    "theirs": "Prefer incoming changes (attack mode)",
    "union": "Combine both changes",
}
