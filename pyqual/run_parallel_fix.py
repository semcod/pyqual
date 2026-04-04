#!/usr/bin/env python3
"""CLI script to run parallel TODO fix with multiple tools.

Runs multiple fix tools in parallel, each processing TODO.md items.
Tools work independently and can process different subsets of issues.
Batch size configurable via --max-items parameter or PYQUAL_MAX_TODOS env var.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .fix_tools import get_available_tools, ToolResult


def get_todo_batch(todo_path: Path, max_items: int) -> tuple[list[tuple[str, str]], int]:
    """Get up to max_items unchecked TODO items and total pending count.
    
    Returns: (batch_items, total_pending)
    batch_items: list of (full_line, item_text) tuples
    """
    if not todo_path.exists():
        return [], 0
    
    content = todo_path.read_text()
    lines = content.splitlines()
    
    pending_items = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            item_text = stripped[6:].strip()
            if item_text:
                pending_items.append((line, item_text))
    
    total_pending = len(pending_items)
    batch = pending_items[:max_items]
    
    return batch, total_pending


def mark_completed_todos(todo_path: Path, changed_files: list[str]) -> int:
    """Mark TODO items as completed if their file was modified.
    
    Returns number of items marked as completed.
    """
    if not todo_path.exists() or not changed_files:
        return 0
    
    content = todo_path.read_text()
    lines = content.splitlines()
    completed = 0
    
    changed_set = set(changed_files)
    changed_basenames = {Path(f).name for f in changed_files}
    
    new_lines = []
    for line in lines:
        if line.strip().startswith("- [ ]"):
            item_text = line.strip()[6:]
            
            file_match = None
            if ":" in item_text:
                potential_file = item_text.split(":")[0].strip()
                if potential_file in changed_set or Path(potential_file).name in changed_basenames:
                    file_match = potential_file
            
            if file_match:
                new_line = line.replace("- [ ]", "- [x]", 1)
                new_lines.append(new_line)
                completed += 1
                print(f"  ✓ Marked completed: {file_match}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    if completed > 0:
        todo_path.write_text("\n".join(new_lines) + "\n")
        print(f"\nUpdated TODO.md: {completed} items marked as completed")
    
    return completed


def run_tool(name: str, command: str, workdir: Path, timeout: int) -> ToolResult:
    """Run a single fix tool and return results."""
    start = time.monotonic()
    print(f"[{name}] Starting...")
    
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ,
        )
        duration = time.monotonic() - start
        success = proc.returncode == 0
        
        print(f"[{name}] {'✓ Done' if success else '✗ Failed'} ({duration:.1f}s)")
        
        return ToolResult(
            name=name,
            success=success,
            returncode=proc.returncode,
            stdout=proc.stdout[-2000:] if proc.stdout else "",
            stderr=proc.stderr[-500:] if proc.stderr else "",
            duration=duration,
        )
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        print(f"[{name}] ✗ Timeout after {timeout}s")
        return ToolResult(
            name=name,
            success=False,
            returncode=-1,
            stdout="",
            stderr=f"Timeout after {timeout}s",
            duration=duration,
        )
    except Exception as e:
        duration = time.monotonic() - start
        print(f"[{name}] ✗ Error: {e}")
        return ToolResult(
            name=name,
            success=False,
            returncode=-2,
            stdout="",
            stderr=str(e),
            duration=duration,
        )


def git_commit_and_push(workdir: Path, completed_count: int) -> bool:
    """Commit changes and push to origin. Returns True if pushed."""
    print("\n📦 Committing changes...")
    
    subprocess.run(["git", "add", "-A"], cwd=workdir, capture_output=True)
    
    commit_result = subprocess.run(
        ["git", "commit", "-m", f"fix: TODO batch ({completed_count} items) [pyqual auto]"],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    
    if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stdout.lower():
        print(f"✗ Commit failed: {commit_result.stderr[:100]}")
        return False
    
    print("📤 Pushing to origin...")
    push_result = subprocess.run(
        ["git", "push", "origin", "HEAD"],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    
    if push_result.returncode == 0:
        print("✓ Pushed successfully")
        return True
    else:
        print(f"✗ Push failed: {push_result.stderr[:100]}")
        return False


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run parallel TODO fix with multiple tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m pyqual.run_parallel_fix           # Use default 5 items per cycle
  python -m pyqual.run_parallel_fix --max 3   # Process 3 items per cycle
  python -m pyqual.run_parallel_fix --max 10  # Process 10 items per cycle

Environment:
  PYQUAL_MAX_TODOS    Default max items per cycle (default: 5, env: PYQUAL_MAX_TODOS)
  LLM_MODEL          LLM model for fix tools (default: openrouter/qwen/qwen3-coder-next)
        """
    )
    parser.add_argument(
        "--max", "--max-items", "-m",
        type=int,
        dest="max_items",
        default=int(os.environ.get("PYQUAL_MAX_TODOS", 5)),
        help="Maximum TODO items to process per cycle (default: 5, env: PYQUAL_MAX_TODOS)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without running tools"
    )
    parser.add_argument(
        "--skip-claude", "-C",
        action="store_true",
        help="Skip Claude Code tool (useful when rate-limited)"
    )
    return parser.parse_args()


def _check_git_changes(workdir: Path) -> list[str]:
    """Check git status and return list of changed files (excluding artifacts)."""
    git_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    changed_files = []
    if git_status.stdout.strip():
        for line in git_status.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                filename = parts[-1]
                if not filename.endswith(('.db', '.jsonl')) and not filename.startswith('.aider'):
                    changed_files.append(filename)
    return changed_files


def _determine_tool_status(result: ToolResult) -> str:
    """Determine tool status based on result."""
    if result.success:
        return "passed"
    if result.returncode == -1:
        return "timeout"
    combined = (result.stdout + result.stderr).lower()
    if "rate limit" in combined or "hit your limit" in combined:
        return "rate_limited"
    if "not found" in combined:
        return "tool_missing"
    return "error"


def _print_yaml_results(
    results: list[ToolResult],
    changed_files: list[str],
    total_pending: int,
    completed_count: int,
    max_items: int,
    batch_size: int,
    duration: float,
    pushed: bool,
) -> None:
    """Print YAML formatted results."""
    succeeded = sum(1 for r in results if r.success)
    failed = len(results) - succeeded
    remaining = total_pending - completed_count

    print("\n# parallel_fix results")
    print(f"todo_items_total: {total_pending}")
    print(f"todo_items_batch: {batch_size}")
    print(f"max_per_cycle: {max_items}")
    print(f"todos_completed: {completed_count}")
    print(f"todos_remaining: {remaining}")
    print(f"duration: {duration:.1f}")
    print("tools:")

    for r in results:
        status = _determine_tool_status(r)
        print(f"  - name: {r.name}")
        print(f"    status: {status}")
        print(f"    returncode: {r.returncode}")
        print(f"    duration: {r.duration:.1f}")

        if not r.success:
            err = r.stderr.strip() or r.stdout.strip() or "unknown"
            err = err[:120].replace("\n", " ").replace('"', "'")
            print(f'    error: "{err}"')

    print("summary:")
    print(f"  succeeded: {succeeded}")
    print(f"  failed: {failed}")
    print(f"  files_changed: {len(changed_files)}")
    print(f"  todos_completed: {completed_count}")
    print(f"  todos_remaining: {remaining}")
    print(f"  git_pushed: {pushed}")

    if changed_files:
        print("  changed:")
        for f in changed_files[:10]:
            print(f"    - {f}")
        if len(changed_files) > 10:
            print(f"    # ... and {len(changed_files) - 10} more")


def _print_cycle_completion(remaining: int, max_items: int) -> None:
    """Print cycle completion message."""
    if remaining > 0:
        print(f"\n🔄 Cycle complete. {remaining} items remaining for next cycle.")
        print(f"   Run again: pyqual run (will process next {min(max_items, remaining)} items)")
    else:
        print("\n✅ All TODO items processed!")


def main() -> int:
    """Run parallel fix on TODO.md items - configurable batch size with git push."""
    args = parse_args()
    
    workdir = Path.cwd()
    todo_path = workdir / "TODO.md"
    batch_file = workdir / ".pyqual" / "todo_batch.md"
    
    if not todo_path.exists():
        print("No TODO.md found — skipping")
        return 0
    
    # Get batch of items
    batch_items, total_pending = get_todo_batch(todo_path, args.max_items)
    
    if not batch_items:
        print("No pending TODO items — skipping")
        return 0
    
    print(f"Processing {len(batch_items)}/{total_pending} TODO items (max {args.max_items} per cycle)")
    for i, (line, text) in enumerate(batch_items, 1):
        print(f"  {i}. {text[:60]}{'...' if len(text) > 60 else ''}")
    
    # Create temp batch file with only these items
    batch_file.parent.mkdir(parents=True, exist_ok=True)
    batch_content = "# TODO Batch (auto-generated)\n\n"
    for line, text in batch_items:
        batch_content += f"- [ ] {text}\n"
    batch_file.write_text(batch_content)
    print(f"\nCreated batch file: {batch_file}")
    
    # Get available tools
    llm_model = os.environ.get("LLM_MODEL")
    tools = get_available_tools(str(batch_file), len(batch_items), llm_model, skip_claude=args.skip_claude)
    
    if not tools:
        print("\nNo fix tools available — skipping")
        if batch_file.exists():
            batch_file.unlink()
        return 0
    
    print(f"\nRunning {len(tools)} tool(s) in parallel...")
    start_time = time.monotonic()
    
    # Convert tools to configs
    tool_configs = [tool.to_config() for tool in tools]
    
    if args.dry_run:
        print("\n[DRY RUN] Would execute:")
        for cfg in tool_configs:
            print(f"  - {cfg['name']}: timeout={cfg['timeout']}s")
        print("\n[DRY RUN] Skipping actual execution")
        return 0
    
    # Run tools in parallel
    results = []
    with ThreadPoolExecutor(max_workers=len(tool_configs)) as executor:
        futures = {
            executor.submit(run_tool, cfg["name"], cfg["command"], workdir, cfg["timeout"]): cfg["name"]
            for cfg in tool_configs
        }
        
        for future in as_completed(futures):
            results.append(future.result())
    
    total_duration = time.monotonic() - start_time
    
    # Check if any changes were made
    changed_files = _check_git_changes(workdir)
    
    # Mark completed TODO items based on changed files
    completed_count = mark_completed_todos(todo_path, changed_files)
    
    # Git commit and push if there are changes
    pushed = False
    if changed_files:
        pushed = git_commit_and_push(workdir, completed_count)
    
    # Cleanup batch file
    if batch_file.exists():
        batch_file.unlink()
    
    # Generate YAML output
    _print_yaml_results(
        results, changed_files, total_pending, completed_count,
        args.max_items, len(batch_items), total_duration, pushed
    )
    
    # Cycle completion message
    remaining = total_pending - completed_count
    _print_cycle_completion(remaining, args.max_items)
    
    failed = sum(1 for r in results if not r.success)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
