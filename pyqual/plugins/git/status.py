from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .git_command import run_git_command


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
    result: dict[str, Any] = {
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

    git_check = run_git_command(["rev-parse", "--git-dir"], cwd=cwd)
    if git_check.returncode != 0:
        result["error"] = "Not a git repository"
        return result

    status_result = run_git_command(["status", "--porcelain", "-b"], cwd=cwd)
    if status_result.returncode != 0:
        result["error"] = status_result.stderr.strip()
        return result

    lines = status_result.stdout.strip().split("\n")
    staged: list[str] = []
    unstaged: list[str] = []
    untracked: list[str] = []

    for line in lines:
        if not line:
            continue
        if line.startswith("##"):
            branch_info = line[3:].strip()
            if "..." in branch_info:
                branch_part = branch_info.split("...")[0]
                result["branch"] = branch_part
                if "[" in branch_info:
                    ahead_behind = branch_info[
                        branch_info.find("[") + 1 : branch_info.find("]")
                    ]
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

        if len(line) >= 3:
            status_code = line[:2]
            filename = line[3:]
            if status_code[0] not in " ?!":
                staged.append(filename)
            elif status_code[1] != " ":
                unstaged.append(filename)
            elif status_code == "??":
                untracked.append(filename)

    result["staged_files"] = staged
    result["unstaged_files"] = unstaged
    result["untracked_files"] = untracked
    result["uncommitted_files"] = staged + unstaged
    result["is_clean"] = not (staged or unstaged or untracked)
    result["success"] = True
    return result
