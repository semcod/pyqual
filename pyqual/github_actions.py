"""GitHub Actions integration for pyqual.

Provides:
- Fetching issues/PRs from GitHub API as tasks
- Posting comments on PRs/issues with failure analysis
- GitHub Actions environment detection and reporting
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class GitHubTask:
    """Represents a task from GitHub (issue or PR)."""
    number: int
    title: str
    body: str
    state: str
    html_url: str
    labels: list[str]
    assignees: list[str]
    source: str  # 'issue' or 'pull_request'
    
    def to_todo_item(self) -> str:
        """Convert to TODO.md format."""
        labels_str = f" [{', '.join(self.labels)}]" if self.labels else ""
        return f"- [ ] #{self.number}: {self.title}{labels_str} ({self.source})"
    
    def __str__(self) -> str:
        return f"#{self.number}: {self.title}"


class GitHubActionsReporter:
    """Reports pyqual results to GitHub Actions and PRs."""
    
    def __init__(self, token: str | None = None, repo: str | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.repo = repo or os.environ.get("GITHUB_REPOSITORY")
        self.event_path = os.environ.get("GITHUB_EVENT_PATH")
        self.event_name = os.environ.get("GITHUB_EVENT_NAME")
        self.sha = os.environ.get("GITHUB_SHA")
        self.ref = os.environ.get("GITHUB_REF")
        
    def is_running_in_github_actions(self) -> bool:
        """Check if running in GitHub Actions environment."""
        return os.environ.get("GITHUB_ACTIONS") == "true"
    
    def get_pr_number(self) -> int | None:
        """Extract PR number from GitHub event."""
        if not self.event_path:
            return None
        
        try:
            event = json.loads(Path(self.event_path).read_text())
            # Try pull_request event
            if "pull_request" in event:
                return event["pull_request"]["number"]
            # Try issue_comment event
            if "issue" in event:
                return event["issue"]["number"]
            return None
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return None
    
    def fetch_issues(self, state: str = "open", labels: str | None = None) -> list[GitHubTask]:
        """Fetch issues from GitHub API."""
        if not self.token or not self.repo:
            return []
        
        cmd = [
            "gh", "issue", "list",
            "--repo", self.repo,
            "--state", state,
            "--json", "number,title,body,state,url,labels,assignees"
        ]
        if labels:
            cmd.extend(["--label", labels])
        
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
                env={**os.environ, "GITHUB_TOKEN": self.token}
            )
            if result.returncode != 0:
                return []
            
            issues = json.loads(result.stdout)
            return [
                GitHubTask(
                    number=i["number"],
                    title=i["title"],
                    body=i.get("body", ""),
                    state=i["state"],
                    html_url=i["url"],
                    labels=[l["name"] for l in i.get("labels", [])],
                    assignees=[a["login"] for a in i.get("assignees", [])],
                    source="issue"
                )
                for i in issues
            ]
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return []
    
    def fetch_pull_requests(self, state: str = "open") -> list[GitHubTask]:
        """Fetch pull requests from GitHub API."""
        if not self.token or not self.repo:
            return []
        
        cmd = [
            "gh", "pr", "list",
            "--repo", self.repo,
            "--state", state,
            "--json", "number,title,body,state,url,labels,assignees"
        ]
        
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
                env={**os.environ, "GITHUB_TOKEN": self.token}
            )
            if result.returncode != 0:
                return []
            
            prs = json.loads(result.stdout)
            return [
                GitHubTask(
                    number=p["number"],
                    title=p["title"],
                    body=p.get("body", ""),
                    state=p["state"],
                    html_url=p["url"],
                    labels=[l["name"] for l in p.get("labels", [])],
                    assignees=[a["login"] for a in p.get("assignees", [])],
                    source="pull_request"
                )
                for p in prs
            ]
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return []
    
    def post_pr_comment(self, body: str, pr_number: int | None = None) -> bool:
        """Post a comment on a PR."""
        pr = pr_number or self.get_pr_number()
        if not pr or not self.token or not self.repo:
            return False
        
        try:
            result = subprocess.run(
                ["gh", "pr", "comment", str(pr), "--repo", self.repo, "--body", body],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "GITHUB_TOKEN": self.token}
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def post_issue_comment(self, body: str, issue_number: int) -> bool:
        """Post a comment on an issue."""
        if not self.token or not self.repo:
            return False
        
        try:
            result = subprocess.run(
                ["gh", "issue", "comment", str(issue_number), "--repo", self.repo, "--body", body],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "GITHUB_TOKEN": self.token}
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def generate_failure_report(
        self,
        stage_name: str,
        error: str,
        logs: str | None = None,
        suggestions: list[str] | None = None
    ) -> str:
        """Generate a formatted failure report for GitHub comment."""
        report = f"""## ❌ Pyqual Pipeline Failure: `{stage_name}`

**Error:** {error}

### Environment
- **Repository:** `{self.repo}`
- **Commit:** `{self.sha[:8] if self.sha else 'N/A'}`
- **Ref:** `{self.ref}`
- **Event:** `{self.event_name}`

"""
        if logs:
            report += f"""### Logs
<details>
<summary>Click to expand</summary>

```
{logs[:3000]}{'...' if len(logs) > 3000 else ''}
```
</details>

"""
        if suggestions:
            report += "### Suggestions\n"
            for s in suggestions:
                report += f"- {s}\n"
            report += "\n"
        
        report += """---
*This comment was automatically generated by [pyqual](https://github.com/semcod/pyqual)*
"""
        return report
    
    def set_output(self, name: str, value: str) -> None:
        """Set GitHub Actions output variable."""
        # Use GITHUB_OUTPUT for new versions
        output_file = os.environ.get("GITHUB_OUTPUT")
        if output_file:
            with open(output_file, "a") as f:
                f.write(f"{name}={value}\n")
        
        # Also set env for compatibility
        print(f"::set-output name={name}::{value}")
    
    def set_failed(self, message: str) -> None:
        """Mark the workflow as failed with a message."""
        print(f"::error::{message}")
