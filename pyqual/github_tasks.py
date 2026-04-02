"""GitHub tasks module for fetching and saving GitHub issues/PRs.

This module provides compatibility functions that were referenced in tests
and CLI but are implemented in github_actions.py.
"""

from pathlib import Path
from typing import List, Optional

from pyqual.github_actions import GitHubActionsReporter, GitHubTask


def fetch_github_tasks(
    label: Optional[str] = None,
    state: str = "open",
    include_issues: bool = True,
    include_prs: bool = True,
) -> List[GitHubTask]:
    """Fetch tasks from GitHub issues and PRs."""
    reporter = GitHubActionsReporter()
    tasks = []
    
    if include_issues:
        issues = reporter.fetch_issues(state=state, labels=label)
        tasks.extend(issues)
    
    if include_prs:
        prs = reporter.fetch_pull_requests(state=state)
        tasks.extend(prs)
    
    return tasks


def save_tasks_to_todo(tasks: list[GitHubTask], todo_path: Path, append: bool = True) -> None:
    """Save tasks to TODO.md file."""
    mode = "a" if append else "w"

    with todo_path.open(mode) as f:
        if not append or (append and not todo_path.exists()):
            f.write("# TODO Tasks from GitHub\n\n")

        for task in tasks:
            f.write(f"{task.to_todo_item()}\n")


def save_tasks_to_json(tasks: list[GitHubTask], json_path: Path) -> None:
    """Save tasks to JSON file."""
    import json

    tasks_data = []
    for task in tasks:
        tasks_data.append({
            "number": task.number,
            "title": task.title,
            "body": task.body,
            "state": task.state,
            "html_url": task.html_url,
            "labels": task.labels,
            "assignees": task.assignees,
            "source": task.source,
        })

    with json_path.open("w") as f:
        json.dump(tasks_data, f, indent=2)
