"""Tickets subcommands.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from pyqual.cli.main import console, tickets_app
from pyqual.tickets import (
    sync_all_tickets,
    sync_github_tickets,
    sync_todo_tickets,
)

if TYPE_CHECKING:
    pass


@tickets_app.command("sync")
def tickets_sync(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Repository root containing pyqual.yaml."),
    from_gates: bool = typer.Option(False, "--from-gates", help="Only sync if gates fail (checks pyqual.yaml gates first)."),
    backends: str = typer.Option("markdown", "--backends", "-b", help="Comma-separated backends: markdown,github,all"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without making changes."),
) -> None:
    """Sync tickets from gate failures or explicitly.
    
    Examples:
        pyqual tickets sync --from-gates              # Check gates, sync if fail
        pyqual tickets sync --from-gates --backends markdown,github
        pyqual tickets sync --from-gates --dry-run    # Preview only
    """
    from pyqual.tickets import sync_from_gates
    
    if from_gates:
        backend_list = [b.strip() for b in backends.split(",")]
        try:
            result = sync_from_gates(workdir=workdir, dry_run=dry_run, backends=backend_list)
            if result["all_passed"]:
                console.print("[green]✅ All gates passed — no tickets needed.[/green]")
            else:
                console.print(f"[yellow]❌ {len(result['failures'])} gate(s) failed: {', '.join(result['failures'])}[/yellow]")
                if result["synced"]:
                    console.print(f"[green]✅ Tickets synced to: {', '.join(result['backends'])}[/green]")
                else:
                    console.print("[dim]Dry run — no changes made.[/dim]")
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)
        except RuntimeError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)
    else:
        console.print("[yellow]Use --from-gates to sync based on gate failures, or use:[/yellow]")
        console.print("  pyqual tickets todo       # Sync TODO.md")
        console.print("  pyqual tickets github       # Sync GitHub Issues")
        console.print("  pyqual tickets all          # Sync all backends")


@tickets_app.command("todo")
def tickets_todo(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Repository root containing TODO.md and .planfile/."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be synced without changing files."),
    direction: str = typer.Option("both", "--direction", help="Sync direction: from, to, or both."),
) -> None:
    """Sync TODO.md tickets using planfile's markdown backend."""
    try:
        sync_todo_tickets(workdir=workdir, dry_run=dry_run, direction=direction)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


@tickets_app.command("github")
def tickets_github(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Repository root containing .planfile/ and GitHub sync config."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be synced without changing files."),
    direction: str = typer.Option("both", "--direction", help="Sync direction: from, to, or both."),
) -> None:
    """Sync GitHub Issues using planfile's GitHub backend."""
    try:
        sync_github_tickets(workdir=workdir, dry_run=dry_run, direction=direction)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


@tickets_app.command("all")
def tickets_all(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Repository root containing TODO.md and .planfile/."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be synced without changing files."),
    direction: str = typer.Option("both", "--direction", help="Sync direction: from, to, or both."),
) -> None:
    """Sync TODO.md and GitHub tickets using planfile."""
    try:
        sync_all_tickets(workdir=workdir, dry_run=dry_run, direction=direction)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


@tickets_app.command("fetch")
def tickets_fetch(
    label: str | None = typer.Option(None, "--label", "-l", help="Filter by label (e.g. 'pyqual-fix')"),
    state: str = typer.Option("open", "--state", "-s", help="Issue state: open, closed, all"),
    output: Path = typer.Option(None, "--output", "-o", help="Output JSON file"),
    todo_output: Path = typer.Option(None, "--todo-output", "-t", help="Append to TODO.md"),
    append: bool = typer.Option(False, "--append", "-a", help="Append to TODO.md instead of overwrite"),
) -> None:
    """Fetch GitHub issues/PRs as tasks.
    
    Examples:
        pyqual tickets fetch --label pyqual-fix
        pyqual tickets fetch --label bug --output tasks.json
        pyqual tickets fetch --todo-output TODO.md --append
    """
    from pyqual.github_tasks import fetch_github_tasks, save_tasks_to_json, save_tasks_to_todo
    
    tasks = fetch_github_tasks(
        label=label,
        state=state,
        include_prs=True,
        include_issues=True,
    )
    
    if not tasks:
        console.print("[yellow]No tasks found matching criteria[/yellow]")
        raise typer.Exit(0)
    
    console.print(f"[bold]Found {len(tasks)} tasks[/bold]")
    for t in tasks:
        console.print(f"  - #{t.number}: {t.title[:50]}{'...' if len(t.title) > 50 else ''}")
    
    if output:
        save_tasks_to_json(tasks, output)
    
    if todo_output:
        save_tasks_to_todo(tasks, todo_output, append=append)


@tickets_app.command("comment")
def tickets_comment(
    issue_number: int = typer.Argument(..., help="Issue or PR number"),
    message: str = typer.Argument(..., help="Comment text"),
    is_pr: bool = typer.Option(False, "--pr", help="Comment on PR instead of issue"),
) -> None:
    """Post a comment on a GitHub issue or PR.
    
    Examples:
        pyqual tickets comment 123 "Fix applied successfully"
        pyqual tickets comment 456 "Failed due to timeout" --pr
    """
    from pyqual.github_actions import GitHubActionsReporter
    
    reporter = GitHubActionsReporter()
    
    if is_pr:
        success = reporter.post_pr_comment(message, issue_number)
    else:
        success = reporter.post_issue_comment(message, issue_number)
    
    if success:
        console.print(f"[green]✅ Comment posted to #{issue_number}[/green]")
    else:
        console.print(f"[red]❌ Failed to post comment[/red]")
        raise typer.Exit(1)
