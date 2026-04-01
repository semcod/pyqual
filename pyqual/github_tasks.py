"""GitHub tasks fetcher for pyqual.

Fetches issues and PRs from GitHub and converts them to TODO items.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .github_actions import GitHubActionsReporter, GitHubTask


def fetch_github_tasks(
    label: str | None = None,
    state: str = "open",
    include_prs: bool = True,
    include_issues: bool = True,
) -> list[GitHubTask]:
    """Fetch tasks from GitHub."""
    reporter = GitHubActionsReporter()
    
    if not reporter.token:
        print("Error: GITHUB_TOKEN not set", file=sys.stderr)
        return []
    
    tasks = []
    
    if include_issues:
        print(f"Fetching issues (state={state}, label={label})...")
        issues = reporter.fetch_issues(state=state, labels=label)
        tasks.extend(issues)
        print(f"  Found {len(issues)} issues")
    
    if include_prs:
        print(f"Fetching pull requests (state={state})...")
        prs = reporter.fetch_pull_requests(state=state)
        tasks.extend(prs)
        print(f"  Found {len(prs)} PRs")
    
    return tasks


def save_tasks_to_todo(tasks: list[GitHubTask], output_path: Path, append: bool = False) -> None:
    """Save tasks to TODO.md format."""
    mode = "a" if append else "w"
    
    with open(output_path, mode) as f:
        if not append or output_path.stat().st_size == 0:
            f.write("# GitHub Tasks (auto-generated)\n\n")
        
        for task in tasks:
            f.write(task.to_todo_item() + "\n")
    
    print(f"Saved {len(tasks)} tasks to {output_path}")


def save_tasks_to_json(tasks: list[GitHubTask], output_path: Path) -> None:
    """Save tasks to JSON for programmatic access."""
    data = [
        {
            "number": t.number,
            "title": t.title,
            "body": t.body,
            "state": t.state,
            "html_url": t.html_url,
            "labels": t.labels,
            "assignees": t.assignees,
            "source": t.source,
        }
        for t in tasks
    ]
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved {len(tasks)} tasks to {output_path}")


def main() -> int:
    """CLI entry point for GitHub tasks fetcher."""
    parser = argparse.ArgumentParser(
        description="Fetch GitHub issues/PRs as pyqual tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m pyqual.github_tasks --fetch-issues --label pyqual-fix
  python -m pyqual.github_tasks --fetch-all --output .pyqual/tasks.json
  python -m pyqual.github_tasks --fetch-prs --state closed
        """
    )
    
    parser.add_argument(
        "--fetch-issues",
        action="store_true",
        help="Fetch GitHub issues"
    )
    parser.add_argument(
        "--fetch-prs",
        action="store_true",
        help="Fetch pull requests"
    )
    parser.add_argument(
        "--fetch-all",
        action="store_true",
        help="Fetch both issues and PRs"
    )
    parser.add_argument(
        "--label",
        type=str,
        help="Filter by label (e.g., 'pyqual-fix', 'bug')"
    )
    parser.add_argument(
        "--state",
        type=str,
        default="open",
        choices=["open", "closed", "all"],
        help="Issue/PR state filter (default: open)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--todo-output",
        type=Path,
        help="Append to TODO.md file"
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing TODO.md instead of overwriting"
    )
    
    args = parser.parse_args()
    
    if not any([args.fetch_issues, args.fetch_prs, args.fetch_all]):
        print("Error: Specify --fetch-issues, --fetch-prs, or --fetch-all", file=sys.stderr)
        return 1
    
    include_issues = args.fetch_issues or args.fetch_all
    include_prs = args.fetch_prs or args.fetch_all
    
    tasks = fetch_github_tasks(
        label=args.label,
        state=args.state,
        include_prs=include_prs,
        include_issues=include_issues,
    )
    
    if not tasks:
        print("No tasks found matching criteria")
        return 0
    
    # Save to JSON if output specified
    if args.output:
        save_tasks_to_json(tasks, args.output)
    
    # Append/save to TODO.md
    if args.todo_output:
        save_tasks_to_todo(tasks, args.todo_output, append=args.append)
    
    # Print summary
    print(f"\n📋 Summary: {len(tasks)} tasks fetched")
    for t in tasks:
        print(f"  - {t}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
