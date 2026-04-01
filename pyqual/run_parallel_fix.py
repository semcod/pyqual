#!/usr/bin/env python3
"""CLI script to run parallel TODO fix with multiple tools.

Runs multiple fix tools in parallel, each processing TODO.md items.
Tools work independently and can process different subsets of issues.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

MAX_TODOS_PER_CYCLE = 5  # Max TODO items to process in one cycle
LLX_TOOL_TIMEOUT = 1800  # 30 minutes for llx fix
AIDER_TOOL_TIMEOUT = 900  # 15 minutes for aider


def count_todo_items(todo_path: Path) -> int:
    """Count pending TODO items in TODO.md."""
    if not todo_path.exists():
        return 0
    content = todo_path.read_text()
    return content.count("- [ ]")


def get_todo_batch(todo_path: Path, max_items: int = MAX_TODOS_PER_CYCLE) -> tuple[list[str], int]:
    """Get up to max_items unchecked TODO items and total pending count.
    
    Returns: (batch_items, total_pending)
    """
    if not todo_path.exists():
        return [], 0
    
    content = todo_path.read_text()
    lines = content.splitlines()
    
    pending_items = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            # Extract just the content after "- [ ]"
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
    
    # Build set of changed file basenames for faster lookup
    changed_set = set(changed_files)
    # Also add just filenames without path for partial matching
    changed_basenames = {Path(f).name for f in changed_files}
    
    new_lines = []
    for line in lines:
        if line.strip().startswith("- [ ]"):
            # Extract file from TODO item (format: "- [ ] file:line - message")
            item_text = line.strip()[6:]  # Remove "- [ ] "
            
            # Try to extract file path
            file_match = None
            if ":" in item_text:
                potential_file = item_text.split(":")[0].strip()
                # Check if this file was changed
                if potential_file in changed_set or Path(potential_file).name in changed_basenames:
                    file_match = potential_file
            
            if file_match:
                # Mark as completed
                new_line = line.replace("- [ ]", "- [x]", 1)
                new_lines.append(new_line)
                completed += 1
                print(f"  ✓ Marked completed: {file_match}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    if completed > 0:
        # Write updated TODO.md
        todo_path.write_text("\n".join(new_lines) + "\n")
        print(f"\nUpdated TODO.md: {completed} items marked as completed")
    
    return completed


def run_tool(name: str, command: str, workdir: Path, timeout: int) -> dict:
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
        
        return {
            "name": name,
            "success": success,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-2000:] if proc.stdout else "",
            "stderr": proc.stderr[-500:] if proc.stderr else "",
            "duration": duration,
        }
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        print(f"[{name}] ✗ Timeout after {timeout}s")
        return {
            "name": name,
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Timeout after {timeout}s",
            "duration": duration,
        }
    except Exception as e:
        duration = time.monotonic() - start
        print(f"[{name}] ✗ Error: {e}")
        return {
            "name": name,
            "success": False,
            "returncode": -2,
            "stdout": "",
            "stderr": str(e),
            "duration": duration,
        }


def main() -> int:
    """Run parallel fix on TODO.md items using multiple tools."""
    workdir = Path.cwd()
    todo_path = workdir / "TODO.md"
    
    if not todo_path.exists():
        print("No TODO.md found — skipping")
        return 0
    
    # Get batch of max 5 items
    batch_items, total_pending = get_todo_batch(todo_path, MAX_TODOS_PER_CYCLE)
    
    if not batch_items:
        print("No pending TODO items — skipping")
        return 0
    
    print(f"Processing {len(batch_items)}/{total_pending} TODO items (max {MAX_TODOS_PER_CYCLE} per cycle)")
    for i, (line, text) in enumerate(batch_items, 1):
        print(f"  {i}. {text[:60]}{'...' if len(text) > 60 else ''}")
    
    # Create temp batch file with only these items
    batch_file = workdir / ".pyqual" / "todo_batch.md"
    batch_file.parent.mkdir(parents=True, exist_ok=True)
    batch_content = "# TODO Batch (auto-generated)\n\n"
    for line, text in batch_items:
        batch_content += f"- [ ] {text}\n"
    batch_file.write_text(batch_content)
    print(f"\nCreated batch file: {batch_file}")
    
    # Define available tools with their commands
    tool_configs = []
    
    # Claude Code - processes TODO items with AI
    if shutil.which("claude"):
        tool_configs.append({
            "name": "claude",
            "command": (
                f'claude -p "Fix these {len(batch_items)} TODO items in this Python project. '
                'Apply minimal, safe changes. Focus on: unused imports, magic numbers, duplicate imports. '
                'Skip dependency updates." '
                '--model sonnet '
                '--allowedTools "Edit,Read,Write,Bash(git diff),Bash(python)" '
                '--output-format text'
            ),
            "timeout": 900,
        })
        print("✓ Claude Code available")
    else:
        print("✗ Claude Code not found")
    
    # llx - processes TODO.md with LLM-driven fixes
    try:
        import llx  # noqa: F401
        llm_model = os.environ.get("LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
        tool_configs.append({
            "name": "llx",
            "command": f"LLM_MODEL={llm_model} llx fix . --apply --errors {batch_file} --verbose",
            "timeout": LLX_TOOL_TIMEOUT,
        })
        print(f"✓ llx available (model={llm_model})")
    except ImportError:
        print("✗ llx not found")
    
    # aider - via Docker (paulgauthier/aider)
    # Uses OPENROUTER_API_KEY and LLM_MODEL from .env
    if shutil.which("docker"):
        # Check if aider image exists
        docker_check = subprocess.run(
            ["docker", "images", "-q", "paulgauthier/aider"],
            capture_output=True, text=True
        )
        if docker_check.stdout.strip():
            # Get model from env, default to openrouter model
            llm_model = os.environ.get("LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
            # aider uses --model flag for model selection
            tool_configs.append({
                "name": "aider",
                "command": (
                    'docker run --rm '
                    f'-v "{workdir}:/app" '
                    '-w /app '
                    '-e OPENROUTER_API_KEY="${OPENROUTER_API_KEY}" '
                    '-e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" '
                    '-e OPENAI_API_KEY="${OPENAI_API_KEY}" '
                    'paulgauthier/aider '
                    f'--model {llm_model} '
                    '--yes --no-git '
                    f'--read {batch_file} '
                    f'--message "Fix these {len(batch_items)} code issues. Focus on: unused imports, magic numbers, duplicate imports. Do NOT modify TODO.md itself."'
                ),
                "timeout": AIDER_TOOL_TIMEOUT,
            })
            print(f"✓ aider available (Docker, model={llm_model})")
        else:
            print("✗ aider Docker image not found (run: docker pull paulgauthier/aider)")
    
    if not tool_configs:
        print("\nNo fix tools available — skipping")
        return 0
    
    print(f"\nRunning {len(tool_configs)} tool(s) in parallel...")
    start_time = time.monotonic()
    
    # Run tools in parallel
    results = []
    with ThreadPoolExecutor(max_workers=len(tool_configs)) as executor:
        futures = {
            executor.submit(
                run_tool,
                cfg["name"],
                cfg["command"],
                workdir,
                cfg["timeout"],
            ): cfg["name"]
            for cfg in tool_configs
        }
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    
    total_duration = time.monotonic() - start_time
    
    # Check if any changes were made
    git_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    changed_files = []
    if git_status.stdout.strip():
        for line in git_status.stdout.strip().splitlines():
            # git status --porcelain format: "XY filename" or "XY old -> new"
            parts = line.split()
            if len(parts) >= 2:
                filename = parts[-1]  # Last part is filename
                # Skip log files and aider artifacts
                if not filename.endswith(('.db', '.jsonl')) and not filename.startswith('.aider'):
                    changed_files.append(filename)
    
    # Mark completed TODO items based on changed files
    completed_count = mark_completed_todos(todo_path, changed_files)
    
    # Git commit and push if there are changes
    pushed = False
    if changed_files:
        print("\n📦 Committing changes...")
        subprocess.run(["git", "add", "-A"], cwd=workdir, capture_output=True)
        commit_result = subprocess.run(
            ["git", "commit", "-m", f"fix: TODO batch ({completed_count} items) [pyqual auto]"],
            cwd=workdir,
            capture_output=True,
            text=True,
        )
        if commit_result.returncode == 0 or "nothing to commit" in commit_result.stdout.lower():
            print("📤 Pushing to origin...")
            push_result = subprocess.run(
                ["git", "push", "origin", "HEAD"],
                cwd=workdir,
                capture_output=True,
                text=True,
            )
            pushed = push_result.returncode == 0
            if pushed:
                print("✓ Pushed successfully")
            else:
                print(f"✗ Push failed: {push_result.stderr[:100]}")
        else:
            print(f"✗ Commit failed: {commit_result.stderr[:100]}")
    
    # Cleanup batch file
    if batch_file.exists():
        batch_file.unlink()
    
    # Generate YAML output for pipeline integration
    succeeded = sum(1 for r in results if r["success"])
    failed = len(results) - succeeded
    remaining = total_pending - completed_count
    
    print("# parallel_fix results")
    print(f"todo_items_total: {total_pending}")
    print(f"todo_items_batch: {len(batch_items)}")
    print(f"todos_completed: {completed_count}")
    print(f"todos_remaining: {remaining}")
    print(f"duration: {total_duration:.1f}")
    print("tools:")
    
    for r in results:
        # Determine status with clear error indication
        combined_output = (r["stdout"] + r["stderr"]).lower()
        if r["success"]:
            status = "passed"
        elif r["returncode"] == -1:
            status = "timeout"
        elif "rate limit" in combined_output or "hit your limit" in combined_output or "resets" in combined_output:
            status = "rate_limited"
        elif "not found" in combined_output or "command not found" in combined_output:
            status = "tool_missing"
        elif "permission denied" in combined_output:
            status = "permission_denied"
        else:
            status = "error"
        
        print(f"  - name: {r['name']}")
        print(f"    status: {status}")
        print(f"    returncode: {r['returncode']}")
        print(f"    duration: {r['duration']:.1f}")
        
        # Add error details if failed
        if not r["success"]:
            # Try stderr first, fallback to stdout for tools that output errors there
            error_msg = r["stderr"].strip() or r["stdout"].strip() or "unknown error"
            error_msg = error_msg[:120].replace("\n", " ").replace('"', "'")
            print(f"    error: \"{error_msg}\"")
    
    # Summary
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
    
    # Cycle completion message
    if remaining > 0:
        print(f"\n🔄 Cycle complete. {remaining} items remaining for next cycle.")
    else:
        print("\n✅ All TODO items processed!")
    
    # Help section - how to get more details
    print("help:")
    print("  logs_db: \".pyqual/pipeline.db\"")
    print("  logs_jsonl: \".pyqual/llx_history.jsonl\"")
    print("  view_logs: \"pyqual logs --last 10\"")
    print("  view_errors: \"pyqual logs --failed\"")
    print("  live_tail: \"pyqual watch\"")
    print("  raw_sql: \"sqlite3 .pyqual/pipeline.db 'SELECT * FROM pipeline_logs ORDER BY id DESC LIMIT 20'\"")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
