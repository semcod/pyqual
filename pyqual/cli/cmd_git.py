"""Git subcommands.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from pyqual.cli.main import console, git_app

if TYPE_CHECKING:
    pass


def _print_file_list(files: list[str], label: str, color: str, prefix: str) -> None:
    """Print a list of files with truncation."""
    if not files:
        return
    console.print(f"\n[{color}]{label} ({len(files)}):[/{color}]")
    for f in files[:10]:
        console.print(f"  {prefix} {f}")
    if len(files) > 10:
        console.print(f"  ... and {len(files) - 10} more")


@git_app.command("status")
def git_status_cmd(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Repository directory"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON to .pyqual/git_status.json"),
) -> None:
    """Show git repository status."""
    from pyqual.git_plugin import git_status

    result = git_status(cwd=workdir)

    if not result["success"]:
        console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
        raise typer.Exit(1)

    # Print status
    if result["is_clean"]:
        console.print("[green]✓ Working directory clean[/green]")
    else:
        console.print("[yellow]⚠ Uncommitted changes[/yellow]")

    _print_file_list(result.get("staged_files", []), "Staged", "green", "+")
    _print_file_list(result.get("unstaged_files", []), "Unstaged", "yellow", "M")
    _print_file_list(result.get("untracked_files", []), "Untracked", "red", "?")

    # Branch info
    console.print(f"\n[dim]Branch: {result['branch']}")
    if result["ahead"] > 0:
        console.print(f"Ahead by {result['ahead']} commit(s)[/dim]")
    if result["behind"] > 0:
        console.print(f"Behind by {result['behind']} commit(s)[/dim]")

    # JSON output
    if json_output:
        output_path = workdir / ".pyqual" / "git_status.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2))
        console.print(f"\n[dim]JSON written to {output_path}[/dim]")


@git_app.command("add")
def git_add_cmd(
    paths: list[str] = typer.Argument(..., help="Files to stage (or -A for all)"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
) -> None:
    """Stage files for commit."""
    from pyqual.git_plugin import git_add
    
    result = git_add(paths=paths, cwd=workdir)
    
    if not result["success"]:
        console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[green]✓ Staged {len(result['files_added'])} file(s)[/green]")


@git_app.command("scan")
def git_scan_cmd(
    paths: list[str] | None = typer.Argument(None, help="Files to scan (default: staged+unstaged)"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    use_trufflehog: bool = typer.Option(True, "--trufflehog/--no-trufflehog", help="Use trufflehog if available"),
    use_gitleaks: bool = typer.Option(True, "--gitleaks/--no-gitleaks", help="Use gitleaks if available"),
    use_patterns: bool = typer.Option(True, "--patterns/--no-patterns", help="Use built-in patterns"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON to .pyqual/git_scan.json"),
    fail_on_findings: bool = typer.Option(True, "--fail/--no-fail", help="Exit with error if secrets found"),
) -> None:
    """Scan files for secrets before push.
    
    Runs multiple scanners in order:
    1. trufflehog (if available) - most comprehensive
    2. gitleaks (if available) - fast regex-based
    3. Built-in patterns - fallback for common secrets
    """
    from pyqual.git_plugin import scan_for_secrets
    
    console.print("[dim]Scanning for secrets...[/dim]")
    
    result = scan_for_secrets(
        paths=paths,
        cwd=workdir,
        use_trufflehog=use_trufflehog,
        use_gitleaks=use_gitleaks,
        use_patterns=use_patterns,
    )
    
    # JSON output
    if json_output:
        output_path = workdir / ".pyqual" / "git_scan.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2))
        console.print(f"[dim]JSON written to {output_path}[/dim]")
    
    # Show results
    scanners = result.get("scanners_used", [])
    console.print(f"[dim]Scanners used: {', '.join(scanners) if scanners else 'none available'}[/dim]")
    console.print(f"[dim]Files scanned: {result.get('total_files_scanned', 0)}[/dim]")
    
    secrets = result.get("secrets_found", [])
    if not secrets:
        console.print("[green]✓ No secrets found[/green]")
        raise typer.Exit(0)
    
    # Group by severity
    critical = [s for s in secrets if s.get("severity") == "CRITICAL"]
    high = [s for s in secrets if s.get("severity") == "HIGH"]
    medium = [s for s in secrets if s.get("severity") == "MEDIUM"]
    low = [s for s in secrets if s.get("severity") == "LOW"]
    
    console.print(f"\n[red]Found {len(secrets)} potential secret(s):[/red]")
    
    def show_findings(findings: list[dict], color: str, label: str) -> None:
        if not findings:
            return
        console.print(f"\n[{color}]{label} ({len(findings)}):[/{color}]")
        for f in findings[:10]:  # Show first 10
            file = f.get("file", "unknown")
            line = f.get("line", 0)
            type_ = f.get("type", "unknown")
            provider = f.get("provider", "Unknown")
            raw = f.get("raw", "")[:30]
            scanner = f.get("scanner", "builtin")
            console.print(f"  [{color}]• {file}:{line} - {type_} ({provider}) via {scanner}[/{color}]")
            if raw:
                console.print(f"    [dim]{raw}[/dim]")
        if len(findings) > 10:
            console.print(f"  [dim]... and {len(findings) - 10} more[/dim]")
    
    show_findings(critical, "red", "CRITICAL")
    show_findings(high, "yellow", "HIGH")
    show_findings(medium, "dim", "MEDIUM")
    show_findings(low, "dim", "LOW")
    
    # Recommendations
    console.print("\n[yellow]Recommendations:[/yellow]")
    console.print("  1. Remove secrets from code and use environment variables")
    console.print("  2. Add to .gitignore if these are test/example values")
    console.print("  3. Use git filter-repo to remove from history if committed")
    
    if fail_on_findings and (critical or high):
        console.print("\n[red]✗ Critical/High severity secrets found - failing[/red]")
        raise typer.Exit(1)
    
    if fail_on_findings and secrets:
        console.print("\n[yellow]⚠ Secrets found - failing (use --no-fail to allow)[/yellow]")
        raise typer.Exit(1)
    
    console.print("\n[yellow]⚠ Secrets found but continuing (--no-fail)[/yellow]")


@git_app.command("commit")
def git_commit_cmd(
    message: str = typer.Option(..., "--message", "-m", help="Commit message"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    add_all: bool = typer.Option(False, "--add-all", "-a", help="Stage all changes before commit"),
    if_changed: bool = typer.Option(False, "--if-changed", help="Only commit if there are changes"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON to .pyqual/git_commit.json"),
) -> None:
    """Create a git commit."""
    from pyqual.git_plugin import git_commit
    
    result = git_commit(
        message=message,
        cwd=workdir,
        add_all=add_all,
        only_if_changed=if_changed,
    )
    
    if result.get("skipped"):
        console.print("[yellow]⚠ No changes to commit[/yellow]")
        if json_output:
            output_path = workdir / ".pyqual" / "git_commit.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(result, indent=2))
        raise typer.Exit(0)
    
    if not result["success"]:
        console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
        raise typer.Exit(1)
    
    commit_hash = result.get("commit_hash", "unknown")
    files_count = len(result.get("files_committed", []))
    console.print(f"[green]✓ Committed {files_count} file(s) as {commit_hash[:8]}[/green]")
    
    if json_output:
        output_path = workdir / ".pyqual" / "git_commit.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2))
        console.print(f"[dim]JSON written to {output_path}[/dim]")


@git_app.command("push")
def git_push_cmd(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    remote: str = typer.Option("origin", "--remote", "-r"),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Branch (default: current)"),
    force: bool = typer.Option(False, "--force", help="Force push (use with caution)"),
    force_with_lease: bool = typer.Option(False, "--force-with-lease", help="Force push with lease (safer)"),
    detect_protection: bool = typer.Option(False, "--detect-protection", help="Detect and report push protection violations"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without pushing (pre-flight check)"),
    scan_secrets: bool = typer.Option(True, "--scan-secrets/--no-scan", help="Scan for secrets before push"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON to .pyqual/git_push.json"),
) -> None:
    """Push commits to remote with push protection detection."""
    from pyqual.git_plugin import git_push, preflight_push_check

    # Pre-flight check
    if dry_run or scan_secrets:
        _run_preflight_checks(workdir, remote, branch, scan_secrets, dry_run, json_output)

    # Actual push
    result = git_push(
        cwd=workdir,
        remote=remote,
        branch=branch,
        force=force,
        force_with_lease=force_with_lease,
    )

    _handle_push_result(result, workdir, remote, json_output, detect_protection)


def _run_preflight_checks(
    workdir: Path, remote: str, branch: str | None, scan_secrets: bool, dry_run: bool, json_output: bool
) -> None:
    """Run pre-flight push checks and handle output."""
    from pyqual.git_plugin import preflight_push_check

    console.print("[dim]Running pre-flight checks...[/dim]")
    preflight = preflight_push_check(
        cwd=workdir,
        remote=remote,
        branch=branch,
        scan_secrets=scan_secrets,
        dry_run=dry_run,
    )

    # Show findings
    if preflight["blockers"]:
        console.print("[red]❌ Push blocked:[/red]")
        for blocker in preflight["blockers"]:
            console.print(f"  [red]• {blocker}[/red]")

    if preflight["warnings"]:
        console.print("[yellow]⚠ Warnings:[/yellow]")
        for warning in preflight["warnings"]:
            console.print(f"  [yellow]• {warning}[/yellow]")

    if dry_run:
        if json_output:
            output_path = workdir / ".pyqual" / "git_preflight.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(preflight, indent=2))
            console.print(f"[dim]JSON written to {output_path}[/dim]")

        if preflight["can_push"]:
            console.print("[green]✓ Pre-flight check passed (dry-run)[/green]")
            raise typer.Exit(0)
        console.print("[red]✗ Pre-flight check failed[/red]")
        raise typer.Exit(1)

    if not preflight["can_push"]:
        console.print("[red]✗ Push blocked by pre-flight checks[/red]")
        raise typer.Exit(1)

    console.print("[green]✓ Pre-flight checks passed[/green]")


def _handle_push_result(
    result: dict, workdir: Path, remote: str, json_output: bool, detect_protection: bool
) -> None:
    """Handle push result and output."""
    # Always write JSON if requested
    if json_output or detect_protection:
        output_path = workdir / ".pyqual" / "git_push.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2))

    if result["push_protection_violation"]:
        console.print("[red]❌ GitHub Push Protection blocked the push![/red]")
        console.print("[yellow]Options:[/yellow]")
        console.print("  1. Disable in repo settings: Settings → Code security → Push Protection")
        console.print("  2. Use --force-with-lease (if you understand the risks)")
        console.print("  3. Remove secrets from commit history")
        for error in result.get("errors", []):
            console.print(f"[dim]  - {error}[/dim]")
        raise typer.Exit(1)

    if not result["success"]:
        console.print(f"[red]Error: Push failed[/red]")
        for error in result.get("errors", []):
            console.print(f"[red]  {error}[/red]")
        raise typer.Exit(1)

    commits = result.get("commits_pushed", 0)
    if commits == 0:
        console.print("[green]✓ Everything up to date[/green]")
    else:
        console.print(f"[green]✓ Pushed {commits} commit(s) to {remote}[/green]")

    if json_output:
        console.print(f"[dim]JSON written to {workdir / '.pyqual' / 'git_push.json'}[/dim]")
