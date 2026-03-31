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


def count_todo_items(todo_path: Path) -> int:
    """Count unchecked items in TODO.md."""
    if not todo_path.exists():
        return 0
    content = todo_path.read_text()
    return sum(1 for line in content.splitlines() if line.strip().startswith("- [ ]"))


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
    
    todo_count = count_todo_items(todo_path)
    if todo_count == 0:
        print("No pending TODO items — skipping")
        return 0
    
    print(f"Found {todo_count} pending TODO items")
    
    # Define available tools with their commands
    # Each tool processes TODO.md independently
    tool_configs = []
    
    # Claude Code - processes TODO items with AI
    if shutil.which("claude"):
        tool_configs.append({
            "name": "claude",
            "command": (
                'claude -p "Process TODO.md items in this Python project. '
                'Fix the issues listed there. Apply minimal, safe changes. '
                'Focus on: unused imports, magic numbers, duplicate imports. '
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
            "command": f"LLM_MODEL={llm_model} llx fix . --apply --errors TODO.md --verbose",
            "timeout": 600,
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
                    '--read TODO.md '  # Read TODO.md as context, don't edit it
                    '--message "Fix the code issues listed in TODO.md. Focus on: unused imports, magic numbers, duplicate imports. Do NOT modify TODO.md itself."'
                ),
                "timeout": 900,
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
    
    # Re-check changed files after TODO.md update
    if completed_count > 0:
        git_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workdir,
            capture_output=True,
            text=True,
        )
        if git_status.stdout.strip():
            changed_files = [
                line.split()[-1] 
                for line in git_status.stdout.strip().splitlines()
                if not line.endswith(('.db', '.jsonl'))
            ]
    
    # Generate YAML output for pipeline integration
    succeeded = sum(1 for r in results if r["success"])
    failed = len(results) - succeeded
    
    print("# parallel_fix results")
    print(f"todo_items: {todo_count}")
    print(f"tools_available: {len(tool_configs)}")
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
    print(f"summary:")
    print(f"  succeeded: {succeeded}")
    print(f"  failed: {failed}")
    print(f"  files_changed: {len(changed_files)}")
    print(f"  todos_completed: {completed_count}")
    
    if changed_files:
        print(f"  changed:")
        for f in changed_files[:10]:
            print(f"    - {f}")
        if len(changed_files) > 10:
            print(f"    # ... and {len(changed_files) - 10} more")
    
    # Help section - how to get more details
    print(f"help:")
    print(f"  logs_db: \".pyqual/pipeline.db\"")
    print(f"  logs_jsonl: \".pyqual/llx_history.jsonl\"")
    print(f"  view_logs: \"pyqual logs --last 10\"")
    print(f"  view_errors: \"pyqual logs --failed\"")
    print(f"  live_tail: \"pyqual watch\"")
    print(f"  raw_sql: \"sqlite3 .pyqual/pipeline.db 'SELECT * FROM pipeline_logs ORDER BY id DESC LIMIT 20'\"")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
