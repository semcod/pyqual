"""Parallel task executor for distributing TODO items across multiple fix tools."""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from typing import Callable

from pyqual.constants import DEFAULT_STAGE_TIMEOUT, LOG_DETAIL_MAX_LEN

log = logging.getLogger("pyqual.parallel")


@dataclass
class FixTool:
    """Configuration for a single fix tool."""
    name: str
    command: str  # Command template with {issue} placeholder
    max_concurrent: int = 1  # How many parallel tasks this tool can handle
    timeout: int = DEFAULT_STAGE_TIMEOUT  # Timeout per task in seconds
    priority: int = 0  # Higher = gets tasks first


@dataclass
class TaskResult:
    """Result of processing a single task."""
    task_id: int
    issue: str
    tool: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    returncode: int = 0


@dataclass
class ParallelRunResult:
    """Result of parallel execution."""
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    results: list[TaskResult] = field(default_factory=list)
    duration: float = 0.0


def parse_todo_items(todo_path: Path) -> list[str]:
    """Parse unchecked items from TODO.md."""
    if not todo_path.exists():
        return []
    
    items = []
    content = todo_path.read_text()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- [ ]"):
            # Extract the issue text after "- [ ] "
            items.append(line[6:].strip())
    return items


def group_similar_issues(issues: list[str], max_group_size: int = 5) -> list[list[str]]:
    """Group similar issues together for batch processing.
    
    Groups by file path prefix (e.g., pyqual/cli.py issues together).
    """
    from collections import defaultdict
    
    file_groups: dict[str, list[str]] = defaultdict(list)
    ungrouped: list[str] = []
    
    for issue in issues:
        # Try to extract file path from issue
        if ":" in issue:
            parts = issue.split(":")
            if parts[0].endswith((".py", ".js", ".ts", ".yaml", ".yml", ".json", ".md")):
                file_groups[parts[0]].append(issue)
                continue
        ungrouped.append(issue)
    
    # Create groups respecting max_group_size
    groups: list[list[str]] = []
    
    for file_issues in file_groups.values():
        for i in range(0, len(file_issues), max_group_size):
            groups.append(file_issues[i:i + max_group_size])
    
    # Add ungrouped items
    for i in range(0, len(ungrouped), max_group_size):
        groups.append(ungrouped[i:i + max_group_size])
    
    return groups


class ParallelExecutor:
    """Executes tasks across multiple fix tools in parallel."""
    
    def __init__(
        self,
        tools: list[FixTool],
        workdir: Path,
        env: dict[str, str] | None = None,
        on_task_done: Callable[[TaskResult], None] | None = None,
    ):
        self.tools = sorted(tools, key=lambda t: -t.priority)  # Higher priority first
        self.workdir = workdir
        self.env = env or {}
        self.on_task_done = on_task_done
        self._task_queue: Queue[tuple[int, str]] = Queue()
        self._results: list[TaskResult] = []
        self._lock = threading.Lock()
        self._task_counter = 0
    
    def _run_tool_task(self, tool: FixTool, task_id: int, issue: str) -> TaskResult:
        """Execute a single task with a specific tool."""
        start = time.monotonic()
        
        # Build command with issue substitution
        command = tool.command.replace("{issue}", issue)
        command = command.replace("{issues}", issue)  # Support both placeholders
        
        log.info("parallel task=%d tool=%s issue=%r", task_id, tool.name, issue[:LOG_DETAIL_MAX_LEN])
        
        try:
            # Merge current environment with custom env to preserve PATH
            run_env = {**os.environ, **self.env}
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=tool.timeout,
                env=run_env,
            )
            
            result = TaskResult(
                task_id=task_id,
                issue=issue,
                tool=tool.name,
                success=proc.returncode == 0,
                stdout=proc.stdout[-2000:] if proc.stdout else "",
                stderr=proc.stderr[-500:] if proc.stderr else "",
                duration=time.monotonic() - start,
                returncode=proc.returncode,
            )
        except subprocess.TimeoutExpired:
            result = TaskResult(
                task_id=task_id,
                issue=issue,
                tool=tool.name,
                success=False,
                stderr=f"Timeout after {tool.timeout}s",
                duration=time.monotonic() - start,
                returncode=-1,
            )
        except Exception as e:
            result = TaskResult(
                task_id=task_id,
                issue=issue,
                tool=tool.name,
                success=False,
                stderr=str(e),
                duration=time.monotonic() - start,
                returncode=-2,
            )
        
        with self._lock:
            self._results.append(result)
        
        if self.on_task_done:
            self.on_task_done(result)
        
        log.info("parallel task=%d tool=%s success=%s duration=%.1fs",
                 task_id, tool.name, result.success, result.duration)
        
        return result
    
    def _tool_worker(self, tool: FixTool) -> list[TaskResult]:
        """Worker that pulls tasks from queue and processes them with given tool."""
        results = []
        
        while True:
            try:
                task_id, issue = self._task_queue.get_nowait()
            except Exception:
                break
            
            result = self._run_tool_task(tool, task_id, issue)
            results.append(result)
            self._task_queue.task_done()
        
        return results
    
    def run(self, issues: list[str], group_similar: bool = True) -> ParallelRunResult:
        """Run all issues across tools in parallel.
        
        Args:
            issues: List of issue strings to process
            group_similar: If True, group similar issues for batch processing
        
        Returns:
            ParallelRunResult with task outcomes
        """
        start = time.monotonic()
        
        if not issues:
            return ParallelRunResult(duration=0.0)
        
        if not self.tools:
            log.warning("No tools configured for parallel execution")
            return ParallelRunResult(total_tasks=len(issues), duration=0.0)
        
        # Optionally group similar issues
        if group_similar:
            groups = group_similar_issues(issues)
            task_items = ["\n".join(g) for g in groups]
        else:
            task_items = issues
        
        # Fill the queue
        for i, item in enumerate(task_items):
            self._task_queue.put((i, item))
        
        total_tasks = len(task_items)
        log.info("parallel_start tools=%d tasks=%d", len(self.tools), total_tasks)
        
        # Calculate total workers across all tools
        total_workers = sum(t.max_concurrent for t in self.tools)
        
        # Create executor with worker threads
        with ThreadPoolExecutor(max_workers=total_workers) as executor:
            futures = []
            
            # Submit workers for each tool based on its max_concurrent
            for tool in self.tools:
                for _ in range(tool.max_concurrent):
                    futures.append(executor.submit(self._tool_worker, tool))
            
            # Wait for all workers to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    log.error("Worker failed: %s", e)
        
        duration = time.monotonic() - start
        
        completed = sum(1 for r in self._results if r.success)
        failed = sum(1 for r in self._results if not r.success)
        
        log.info("parallel_done tasks=%d completed=%d failed=%d duration=%.1fs",
                 total_tasks, completed, failed, duration)
        
        return ParallelRunResult(
            total_tasks=total_tasks,
            completed=completed,
            failed=failed,
            results=self._results,
            duration=duration,
        )


def run_parallel_fix(
    workdir: Path,
    tools: list[dict],
    todo_path: Path | None = None,
    issues: list[str] | None = None,
    env: dict[str, str] | None = None,
    group_similar: bool = True,
    on_task_done: Callable[[TaskResult], None] | None = None,
) -> ParallelRunResult:
    """Convenience function to run parallel fix with multiple tools.
    
    Args:
        workdir: Working directory for commands
        tools: List of tool configs [{"name": "claude", "command": "...", "max_concurrent": 2}]
        todo_path: Path to TODO.md (optional if issues provided)
        issues: List of issue strings (optional if todo_path provided)
        env: Environment variables
        group_similar: Group similar issues for batch processing
        on_task_done: Callback for each completed task
    
    Returns:
        ParallelRunResult
    """
    # Parse issues from TODO.md if not provided
    if issues is None:
        if todo_path is None:
            todo_path = workdir / "TODO.md"
        issues = parse_todo_items(todo_path)
    
    if not issues:
        log.info("No issues to process")
        return ParallelRunResult()
    
    # Convert tool dicts to FixTool objects
    fix_tools = [
        FixTool(
            name=t.get("name", f"tool_{i}"),
            command=t.get("command", ""),
            max_concurrent=t.get("max_concurrent", 1),
            timeout=t.get("timeout", DEFAULT_STAGE_TIMEOUT),
            priority=t.get("priority", 0),
        )
        for i, t in enumerate(tools)
        if t.get("command")
    ]
    
    if not fix_tools:
        log.warning("No valid tools configured")
        return ParallelRunResult(total_tasks=len(issues))
    
    executor = ParallelExecutor(
        tools=fix_tools,
        workdir=workdir,
        env=env,
        on_task_done=on_task_done,
    )
    
    return executor.run(issues, group_similar=group_similar)
