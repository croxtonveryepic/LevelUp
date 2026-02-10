"""Typer CLI commands: run, detect, config, gui, status, version, self-update."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

from levelup.cli.display import (
    console,
    get_version_string,
    print_banner,
    print_error,
    print_project_info,
)

app = typer.Typer(
    name="levelup",
    help="AI-Powered TDD Development Tool",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(get_version_string())
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """AI-Powered TDD Development Tool."""


@app.command()
def run(
    task: Optional[str] = typer.Argument(None, help="Task description (or omit for interactive)"),
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Claude model to use"),
    no_checkpoints: bool = typer.Option(False, "--no-checkpoints", help="Skip user checkpoints"),
    max_iterations: Optional[int] = typer.Option(
        None, "--max-iterations", help="Max code iteration cycles"
    ),
    headless: bool = typer.Option(
        False, "--headless", help="Run without terminal; checkpoints via GUI"
    ),
    gui_mode: bool = typer.Option(
        False, "--gui", help="GUI mode: DB checkpoints with visible output"
    ),
    db_path: Optional[Path] = typer.Option(
        None, "--db-path", help="Override state DB path (default: ~/.levelup/state.db)"
    ),
    backend: Optional[str] = typer.Option(
        None, "--backend", help="Backend: 'claude_code' (default) or 'anthropic_sdk'"
    ),
    ticket_next: bool = typer.Option(
        False, "--ticket-next", "-T", help="Auto-pick next pending ticket"
    ),
    ticket: Optional[int] = typer.Option(
        None, "--ticket", "-t", help="Run a specific ticket by number"
    ),
) -> None:
    """Run the LevelUp TDD pipeline on a task."""
    from levelup.cli.prompts import get_task_input
    from levelup.config.loader import load_settings
    from levelup.core.context import PipelineContext, TaskInput
    from levelup.core.orchestrator import Orchestrator
    from levelup.state.manager import StateManager

    if not headless and not gui_mode:
        print_banner()

    # Headless/GUI mode requires a task (can't prompt interactively)
    if (headless or gui_mode) and not task and not ticket_next and ticket is None:
        print_error("--headless/--gui requires a task argument or --ticket/--ticket-next.")
        raise typer.Exit(1)

    # Build settings overrides from CLI args
    overrides: dict = {}
    if model:
        overrides.setdefault("llm", {})["model"] = model
    if max_iterations:
        overrides.setdefault("pipeline", {})["max_code_iterations"] = max_iterations
    if no_checkpoints:
        overrides.setdefault("pipeline", {})["require_checkpoints"] = False
    if backend:
        overrides.setdefault("llm", {})["backend"] = backend

    settings = load_settings(project_path=path, overrides=overrides)
    settings.project.path = path.resolve()

    # Auth: only needed for anthropic_sdk backend
    if settings.llm.backend == "anthropic_sdk":
        from levelup.config.auth import get_claude_code_api_key

        api_key = settings.llm.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            claude_code_token = get_claude_code_api_key()
            if claude_code_token:
                settings.llm.auth_token = claude_code_token
            else:
                print_error(
                    "No API key found. Set ANTHROPIC_API_KEY env var or add to config file."
                )
                raise typer.Exit(1)
        else:
            settings.llm.api_key = api_key

    # Get task
    if ticket_next:
        from levelup.core.tickets import TicketStatus, get_next_ticket, set_ticket_status

        t = get_next_ticket(path, settings.project.tickets_file)
        if not t:
            print_error("No pending tickets.")
            raise typer.Exit(1)
        set_ticket_status(path, t.number, TicketStatus.IN_PROGRESS, settings.project.tickets_file)
        task_input = t.to_task_input()
        console.print(f"[cyan]Ticket #{t.number}:[/cyan] {t.title}")
    elif ticket is not None:
        from levelup.core.tickets import TicketStatus, read_tickets, set_ticket_status

        tickets = read_tickets(path, settings.project.tickets_file)
        matching = [tk for tk in tickets if tk.number == ticket]
        if not matching:
            print_error(f"Ticket #{ticket} not found.")
            raise typer.Exit(1)
        t = matching[0]
        set_ticket_status(path, t.number, TicketStatus.IN_PROGRESS, settings.project.tickets_file)
        task_input = t.to_task_input()
        console.print(f"[cyan]Ticket #{t.number}:[/cyan] {t.title}")
    elif task:
        task_input = TaskInput(title=task, description="")
    else:
        title, description = get_task_input()
        if not title:
            print_error("Task title is required.")
            raise typer.Exit(1)
        task_input = TaskInput(title=title, description=description)

    # Create state manager (always, so all runs are visible in GUI)
    state_mgr_kwargs = {}
    if db_path:
        state_mgr_kwargs["db_path"] = db_path
    state_manager = StateManager(**state_mgr_kwargs)

    # Run pipeline
    orchestrator = Orchestrator(
        settings=settings,
        state_manager=state_manager,
        headless=headless,
        gui_mode=gui_mode,
    )
    ctx = orchestrator.run(task_input)

    # Auto-mark ticket as done on successful completion
    if ctx.status.value == "completed" and ctx.task.source == "ticket" and ctx.task.source_id:
        from levelup.core.tickets import TicketStatus, set_ticket_status

        try:
            ticket_num = int(ctx.task.source_id.split(":")[1])
            set_ticket_status(path, ticket_num, TicketStatus.DONE, settings.project.tickets_file)
            console.print(f"[green]Ticket #{ticket_num} marked as done.[/green]")
        except (IndexError, ValueError):
            pass

    if ctx.status.value == "failed":
        print_error(f"Pipeline failed: {ctx.error_message}")
        raise typer.Exit(1)


@app.command()
def detect(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path to analyze"),
) -> None:
    """Detect project language, framework, and test runner."""
    from levelup.detection.detector import ProjectDetector

    print_banner()
    detector = ProjectDetector()
    info = detector.detect(path)
    print_project_info(info)


@app.command()
def config(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
) -> None:
    """Show current configuration."""
    from levelup.config.loader import find_config_file, load_settings

    print_banner()
    settings = load_settings(project_path=path)

    config_file = find_config_file(path)
    if config_file:
        console.print(f"Config file: [cyan]{config_file}[/cyan]")
    else:
        console.print("[dim]No config file found (using defaults)[/dim]")

    console.print(f"\n[bold]LLM:[/bold]")
    console.print(f"  Model: {settings.llm.model}")
    console.print(f"  Max tokens: {settings.llm.max_tokens}")
    console.print(f"  Temperature: {settings.llm.temperature}")
    console.print(f"  API key: {'***set***' if settings.llm.api_key else '[red]not set[/red]'}")
    console.print(f"  Backend: {settings.llm.backend}")

    console.print(f"\n[bold]Pipeline:[/bold]")
    console.print(f"  Max code iterations: {settings.pipeline.max_code_iterations}")
    console.print(f"  Require checkpoints: {settings.pipeline.require_checkpoints}")
    console.print(f"  Create git branch: {settings.pipeline.create_git_branch}")


def _get_gui_install_hint() -> str:
    """Return a context-aware install hint for GUI support."""
    meta = _load_install_meta()
    method = (meta or {}).get("method", "")
    if method == "global":
        return (
            "GUI support is not installed. To add it:\n"
            "  levelup self-update --gui"
        )
    elif method == "editable":
        return (
            "GUI support is not installed. To add it:\n"
            '  uv pip install -e ".[gui]" --python '
            + sys.executable
        )
    else:
        return (
            "GUI support is not installed. To add it:\n"
            '  uv pip install PyQt6>=6.6.0 --python '
            + sys.executable
        )


def _auto_install_gui() -> bool:
    """Attempt to install GUI support. Returns True on success."""
    meta = _load_install_meta()
    method = (meta or {}).get("method", "")

    if method == "global":
        source_path = (meta or {}).get("source_path", "")
        # Check if source_path exists; if not, fall back to remote URL
        if source_path and Path(source_path).is_dir():
            install_target = f"{source_path}[gui]"
        else:
            # Try repo_url from metadata, then default
            repo_url = (meta or {}).get("repo_url", "") or DEFAULT_REPO_URL
            install_target = f"levelup[gui] @ {_normalize_git_url(repo_url)}"
        console.print("[dim]Installing GUI via uv tool...[/dim]")
        result = subprocess.run(
            ["uv", "tool", "install", "--force", install_target],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print_error(f"Install failed:\n{result.stderr.strip()}")
            return False
        # Update extras in metadata
        if meta is None:
            meta = {}
        extras = meta.get("extras", [])
        if "gui" not in extras:
            extras.append("gui")
            meta["extras"] = extras
            _save_install_meta(meta)
        # Global rebuild — can't re-import in this process
        console.print(
            "[bold green]GUI support installed.[/bold green] "
            "Please re-run [cyan]levelup gui[/cyan]."
        )
        return False  # Signal caller to exit 0 (success but can't launch)
    else:
        # Editable or no metadata — install into current venv
        if method == "editable":
            install_spec = [
                sys.executable, "-m", "uv", "pip", "install", "-e", ".[gui]",
                "--python", sys.executable,
            ]
        else:
            install_spec = [
                sys.executable, "-m", "uv", "pip", "install", "PyQt6>=6.6.0",
                "--python", sys.executable,
            ]
        console.print("[dim]Installing GUI dependencies...[/dim]")
        result = subprocess.run(
            install_spec,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print_error(f"Install failed:\n{result.stderr.strip()}")
            return False
        # Update extras in metadata if present
        if meta is not None:
            extras = meta.get("extras", [])
            if "gui" not in extras:
                extras.append("gui")
                meta["extras"] = extras
                _save_install_meta(meta)
        return True  # Can re-import in this process


@app.command()
def gui(
    db_path: Optional[Path] = typer.Option(
        None, "--db-path", help="Override state DB path"
    ),
    project_path: Optional[Path] = typer.Option(
        None, "--project-path", "-p", help="Project path (enables ticket sidebar)"
    ),
) -> None:
    """Launch the LevelUp GUI dashboard."""
    try:
        from levelup.gui.app import launch_gui
    except ImportError:
        hint = _get_gui_install_hint()
        if sys.stdin.isatty():
            from levelup.cli.prompts import confirm_action

            console.print(f"[yellow]{hint}[/yellow]")
            if confirm_action("Install GUI support now?"):
                success = _auto_install_gui()
                if success:
                    # Editable / direct install — try re-importing
                    try:
                        from levelup.gui.app import launch_gui as lg

                        lg(db_path=db_path, project_path=project_path)
                        return
                    except ImportError:
                        print_error(
                            "Install succeeded but import still failed. "
                            "Please restart your shell and try again."
                        )
                        raise typer.Exit(1)
                else:
                    # Global install printed "re-run" message, or install failed
                    raise typer.Exit(0)
            else:
                raise typer.Exit(1)
        else:
            print_error(hint)
            raise typer.Exit(1)

    launch_gui(db_path=db_path, project_path=project_path)


@app.command()
def status(
    db_path: Optional[Path] = typer.Option(
        None, "--db-path", help="Override state DB path"
    ),
) -> None:
    """Show status of all LevelUp runs in the terminal."""
    from rich.table import Table

    from levelup.state.manager import StateManager

    mgr_kwargs = {}
    if db_path:
        mgr_kwargs["db_path"] = db_path
    mgr = StateManager(**mgr_kwargs)

    # Clean up dead processes
    mgr.mark_dead_runs()

    runs = mgr.list_runs()

    if not runs:
        console.print("[dim]No runs found.[/dim]")
        return

    table = Table(title="LevelUp Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Task", max_width=40)
    table.add_column("Project", max_width=30)
    table.add_column("Status")
    table.add_column("Step")
    table.add_column("Cost", justify="right")
    table.add_column("Started")

    status_styles = {
        "running": "blue",
        "waiting_for_input": "yellow",
        "paused": "yellow",
        "completed": "green",
        "failed": "red",
        "aborted": "dim",
        "pending": "dim",
    }

    for r in runs:
        style = status_styles.get(r.status, "")
        status_display = f"[{style}]{r.status}[/{style}]" if style else r.status
        cost_display = f"${r.total_cost_usd:.4f}" if r.total_cost_usd else "-"
        table.add_row(
            r.run_id[:12],
            r.task_title,
            r.project_path,
            status_display,
            r.current_step or "",
            cost_display,
            r.started_at[:19],
        )

    console.print(table)

    # Summary
    active = sum(1 for r in runs if r.status in ("running", "pending"))
    awaiting = sum(1 for r in runs if r.status == "waiting_for_input")
    if active or awaiting:
        console.print(
            f"\n[bold]{active} active[/bold], "
            f"[yellow]{awaiting} awaiting input[/yellow]"
        )


@app.command()
def resume(
    run_id: Optional[str] = typer.Argument(None, help="Run ID to resume (omit to pick interactively)"),
    from_step: Optional[str] = typer.Option(None, "--from-step", help="Step to resume from (default: where it failed)"),
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Claude model override"),
    backend: Optional[str] = typer.Option(None, "--backend", help="Backend override"),
    db_path: Optional[Path] = typer.Option(
        None, "--db-path", help="Override state DB path"
    ),
) -> None:
    """Resume a failed or aborted pipeline run."""
    from levelup.config.loader import load_settings
    from levelup.core.context import PipelineContext, PipelineStatus
    from levelup.core.orchestrator import Orchestrator
    from levelup.state.manager import StateManager

    print_banner()

    # Open state DB
    mgr_kwargs = {}
    if db_path:
        mgr_kwargs["db_path"] = db_path
    state_manager = StateManager(**mgr_kwargs)

    # Interactive picker when no run_id provided
    if run_id is None:
        from levelup.cli.prompts import pick_resumable_run

        state_manager.mark_dead_runs()
        all_runs = state_manager.list_runs()
        resumable = [
            r for r in all_runs
            if r.status in ("failed", "aborted", "paused") and r.context_json
        ]
        if not resumable:
            console.print("[yellow]No resumable runs found.[/yellow]")
            raise typer.Exit(0)
        record = pick_resumable_run(resumable)
        run_id = record.run_id
    else:
        # Look up run by explicit ID
        record = state_manager.get_run(run_id)
        if record is None:
            print_error(f"Run '{run_id}' not found.")
            raise typer.Exit(1)

        if record.status not in ("failed", "aborted", "paused"):
            print_error(f"Run '{run_id}' has status '{record.status}' — only failed, aborted, or paused runs can be resumed.")
            raise typer.Exit(1)

        if not record.context_json:
            print_error(f"Run '{run_id}' has no saved context — cannot resume.")
            raise typer.Exit(1)

    # Deserialize context
    ctx = PipelineContext.model_validate_json(record.context_json)

    # Load settings with CLI overrides
    overrides: dict = {}
    if model:
        overrides.setdefault("llm", {})["model"] = model
    if backend:
        overrides.setdefault("llm", {})["backend"] = backend

    settings = load_settings(project_path=path, overrides=overrides)
    settings.project.path = path.resolve()

    # Auth (same as run command)
    if settings.llm.backend == "anthropic_sdk":
        from levelup.config.auth import get_claude_code_api_key

        api_key = settings.llm.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            claude_code_token = get_claude_code_api_key()
            if claude_code_token:
                settings.llm.auth_token = claude_code_token
            else:
                print_error("No API key found.")
                raise typer.Exit(1)
        else:
            settings.llm.api_key = api_key

    # Resume
    orchestrator = Orchestrator(settings=settings, state_manager=state_manager)
    ctx = orchestrator.resume(ctx, from_step=from_step)

    if ctx.status.value == "failed":
        print_error(f"Pipeline failed: {ctx.error_message}")
        raise typer.Exit(1)


@app.command()
def rollback(
    run_id: str = typer.Argument(..., help="Run ID to roll back"),
    to: Optional[str] = typer.Option(None, "--to", help="Roll back to this step's commit (default: pre-run state)"),
    db_path: Optional[Path] = typer.Option(
        None, "--db-path", help="Override state DB path"
    ),
) -> None:
    """Roll back a pipeline run to a previous state via git reset."""
    from levelup.core.context import PipelineContext
    from levelup.state.manager import StateManager

    print_banner()

    # Open state DB
    mgr_kwargs = {}
    if db_path:
        mgr_kwargs["db_path"] = db_path
    state_manager = StateManager(**mgr_kwargs)

    record = state_manager.get_run(run_id)
    if record is None:
        print_error(f"Run '{run_id}' not found.")
        raise typer.Exit(1)

    if not record.context_json:
        print_error(f"Run '{run_id}' has no saved context — cannot rollback.")
        raise typer.Exit(1)

    ctx = PipelineContext.model_validate_json(record.context_json)

    if not ctx.pre_run_sha:
        print_error("No pre-run SHA recorded — this run did not create a git branch. Cannot rollback.")
        raise typer.Exit(1)

    # Determine target SHA
    if to:
        sha = ctx.step_commits.get(to)
        if not sha:
            available = ", ".join(ctx.step_commits.keys()) if ctx.step_commits else "none"
            print_error(f"No commit found for step '{to}'. Available: {available}")
            raise typer.Exit(1)
        target_sha = sha
    else:
        target_sha = ctx.pre_run_sha

    # Perform git reset
    try:
        import git
        from levelup.core.orchestrator import Orchestrator
        from levelup.config.settings import LevelUpSettings, LLMSettings, PipelineSettings, ProjectSettings

        project_path = ctx.project_path
        repo = git.Repo(str(project_path))

        # Build expected branch name using stored convention
        convention = ctx.branch_naming or "levelup/{run_id}"
        # Create a temporary orchestrator just to use the helper method
        temp_settings = LevelUpSettings(
            llm=LLMSettings(api_key="temp", model="temp", backend="claude_code"),
            project=ProjectSettings(path=project_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        temp_orch = Orchestrator(settings=temp_settings)
        branch_name = temp_orch._build_branch_name(convention, ctx)

        # Clean up worktree if this run used one
        if ctx.worktree_path:
            try:
                if ctx.worktree_path.exists():
                    repo.git.worktree("remove", str(ctx.worktree_path), "--force")
                    console.print(f"[dim]Removed worktree: {ctx.worktree_path}[/dim]")
            except Exception as wt_err:
                console.print(f"[yellow]Warning: failed to remove worktree: {wt_err}[/yellow]")

        # Rolling back to pre-run state: delete the branch entirely
        if not to:
            if branch_name in [h.name for h in repo.heads]:
                # Ensure we're not on the branch we're about to delete
                current = repo.active_branch.name if not repo.head.is_detached else None
                if current == branch_name:
                    # Detach HEAD or checkout default branch
                    repo.git.checkout(target_sha)
                repo.delete_head(branch_name, force=True)
                console.print(f"[dim]Deleted branch: {branch_name}[/dim]")
            console.print(f"[green]Rolled back to pre-run state ({target_sha[:12]})[/green]")
        else:
            # Rolling back to a step: reset within the branch
            # Operate on the worktree repo if it existed, else main repo
            if branch_name in [h.name for h in repo.heads]:
                current = repo.active_branch.name if not repo.head.is_detached else None
                if current and current != branch_name:
                    console.print(f"[yellow]Warning: currently on branch '{current}', expected '{branch_name}'[/yellow]")
            repo.git.reset("--hard", target_sha)
            console.print(f"[green]Reset to {target_sha[:12]}[/green]")

    except Exception as e:
        print_error(f"Git reset failed: {e}")
        raise typer.Exit(1)

    # Update run status to aborted in DB
    from levelup.core.context import PipelineStatus
    ctx.status = PipelineStatus.ABORTED
    state_manager.update_run(ctx)
    console.print(f"Run '{run_id}' marked as aborted.")


@app.command()
def forget(
    run_id: Optional[str] = typer.Argument(None, help="Run ID to delete (omit for interactive picker)"),
    nuke: bool = typer.Option(False, "--nuke", help="Delete ALL runs from the database"),
    db_path: Optional[Path] = typer.Option(
        None, "--db-path", help="Override state DB path (default: ~/.levelup/state.db)"
    ),
) -> None:
    """Delete a pipeline run from the state database."""
    from levelup.state.manager import StateManager

    print_banner()

    mgr_kwargs: dict = {}
    if db_path:
        mgr_kwargs["db_path"] = db_path
    state_manager = StateManager(**mgr_kwargs)

    if nuke:
        # --nuke: delete all runs
        runs = state_manager.list_runs()
        if not runs:
            console.print("[dim]No runs to delete.[/dim]")
            return

        from levelup.cli.prompts import confirm_action

        console.print(f"[bold red]This will delete {len(runs)} run(s).[/bold red]")
        if not confirm_action(f"Delete all {len(runs)} runs?", default=False):
            console.print("[dim]Cancelled.[/dim]")
            return

        errors = []
        for r in runs:
            try:
                state_manager.delete_run(r.run_id)
            except Exception as e:
                errors.append((r.run_id, str(e)))

        if errors:
            for rid, err in errors:
                console.print(f"[red]Error deleting {rid}: {err}[/red]")
            raise typer.Exit(1)

        console.print(f"[green]Deleted {len(runs)} run(s).[/green]")
        return

    if run_id is not None:
        # Explicit run ID
        if not run_id.strip():
            print_error("Run ID cannot be empty.")
            raise typer.Exit(1)

        record = state_manager.get_run(run_id)
        if record is None:
            print_error(f"Run '{run_id}' not found.")
            raise typer.Exit(1)

        try:
            state_manager.delete_run(run_id)
        except Exception as e:
            print_error(f"Error deleting run: {e}")
            raise typer.Exit(1)

        console.print(f"[green]Run '{run_id}' deleted.[/green]")
        return

    # Interactive mode: pick a run to delete
    state_manager.mark_dead_runs()
    runs = state_manager.list_runs()
    if not runs:
        console.print("[dim]No runs found.[/dim]")
        return

    from levelup.cli.prompts import confirm_action, pick_run_to_forget

    try:
        selected = pick_run_to_forget(runs)
    except KeyboardInterrupt:
        return

    if not confirm_action(f"Delete run '{selected.run_id[:12]}'?", default=False):
        console.print("[dim]Cancelled.[/dim]")
        return

    state_manager.delete_run(selected.run_id)
    console.print(f"[green]Run '{selected.run_id}' deleted.[/green]")


@app.command()
def instruct(
    action: str = typer.Argument("list", help="Action: add, list, or remove"),
    text: Optional[str] = typer.Argument(None, help="Instruction text (add) or index (remove)"),
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
) -> None:
    """Add, list, or remove project rules in CLAUDE.md."""
    from levelup.core.instructions import (
        add_instruction,
        read_instructions,
        remove_instruction,
    )

    if action == "add":
        if not text:
            print_error("Please provide the rule text: levelup instruct add \"rule text\"")
            raise typer.Exit(1)
        add_instruction(path, text)
        console.print(f"[green]Added rule:[/green] {text}")

    elif action == "list":
        rules = read_instructions(path)
        if not rules:
            console.print("[dim]No project rules found in CLAUDE.md.[/dim]")
            return
        console.print("[bold]Project Rules:[/bold]")
        for i, rule in enumerate(rules, 1):
            console.print(f"  {i}. {rule}")

    elif action == "remove":
        if not text:
            print_error("Please provide the rule index: levelup instruct remove 1")
            raise typer.Exit(1)
        try:
            index = int(text)
        except ValueError:
            print_error(f"Invalid index: {text}")
            raise typer.Exit(1)
        try:
            removed = remove_instruction(path, index)
            console.print(f"[green]Removed rule #{index}:[/green] {removed}")
        except IndexError as e:
            print_error(str(e))
            raise typer.Exit(1)

    else:
        print_error(f"Unknown action: {action}. Use add, list, or remove.")
        raise typer.Exit(1)


@app.command()
def tickets(
    action: str = typer.Argument("list", help="Action: list, next, start, done, merged, or delete"),
    ticket_num: Optional[int] = typer.Argument(None, help="Ticket number (for start/done/merged/delete)"),
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
) -> None:
    """List and manage tickets from the tickets markdown file."""
    from rich.table import Table

    from levelup.config.loader import load_settings
    from levelup.core.tickets import (
        TicketStatus,
        delete_ticket,
        get_next_ticket,
        read_tickets,
        set_ticket_status,
    )

    settings = load_settings(project_path=path)

    if action == "list":
        all_tickets = read_tickets(path, settings.project.tickets_file)
        if not all_tickets:
            console.print("[dim]No tickets found.[/dim]")
            return

        table = Table(title="Tickets")
        table.add_column("#", style="bold", justify="right")
        table.add_column("Title")
        table.add_column("Status")

        status_styles = {
            TicketStatus.PENDING: "white",
            TicketStatus.IN_PROGRESS: "yellow",
            TicketStatus.DONE: "green",
            TicketStatus.MERGED: "dim",
        }

        for t in all_tickets:
            style = status_styles.get(t.status, "")
            status_display = f"[{style}]{t.status.value}[/{style}]"
            table.add_row(str(t.number), t.title, status_display)

        console.print(table)

    elif action == "next":
        t = get_next_ticket(path, settings.project.tickets_file)
        if t:
            console.print(f"[cyan]#{t.number}[/cyan] {t.title}")
            if t.description:
                console.print(f"[dim]{t.description}[/dim]")
        else:
            console.print("[dim]No pending tickets.[/dim]")

    elif action in ("start", "done", "merged"):
        if ticket_num is None:
            print_error(f"Ticket number required: levelup tickets {action} <N>")
            raise typer.Exit(1)
        status_map = {
            "start": TicketStatus.IN_PROGRESS,
            "done": TicketStatus.DONE,
            "merged": TicketStatus.MERGED,
        }
        new_status = status_map[action]
        try:
            set_ticket_status(path, ticket_num, new_status, settings.project.tickets_file)
            console.print(f"[green]Ticket #{ticket_num} → {new_status.value}[/green]")
        except IndexError as e:
            print_error(str(e))
            raise typer.Exit(1)

    elif action == "delete":
        if ticket_num is None:
            print_error("Ticket number required: levelup tickets delete <N>")
            raise typer.Exit(1)
        try:
            title = delete_ticket(path, ticket_num, settings.project.tickets_file)
            console.print(f"[green]Deleted ticket #{ticket_num}: {title}[/green]")
        except IndexError as e:
            print_error(str(e))
            raise typer.Exit(1)

    else:
        print_error(f"Unknown action: {action}. Use list, next, start, done, merged, or delete.")
        raise typer.Exit(1)


@app.command()
def recon(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path to explore"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Claude model to use"),
    backend: Optional[str] = typer.Option(
        None, "--backend", help="Backend: 'claude_code' (default) or 'anthropic_sdk'"
    ),
) -> None:
    """Run one-time project reconnaissance to enrich project_context.md."""
    from rich.table import Table

    from levelup.agents.backend import ClaudeCodeBackend
    from levelup.agents.claude_code_client import ClaudeCodeClient
    from levelup.agents.recon import ReconAgent
    from levelup.config.loader import load_settings
    from levelup.detection.detector import ProjectDetector

    print_banner()

    # Build settings with CLI overrides
    overrides: dict = {}
    if model:
        overrides.setdefault("llm", {})["model"] = model
    if backend:
        overrides.setdefault("llm", {})["backend"] = backend

    settings = load_settings(project_path=path, overrides=overrides)
    settings.project.path = path.resolve()

    # Run detection
    console.print("[bold]Detecting project...[/bold]")
    detector = ProjectDetector()
    info = detector.detect(path)
    print_project_info(info)

    # Create backend
    if settings.llm.backend == "claude_code":
        client = ClaudeCodeClient(
            model=settings.llm.model,
            claude_executable=settings.llm.claude_executable,
        )
        be = ClaudeCodeBackend(client)
    else:
        from levelup.agents.backend import AnthropicSDKBackend
        from levelup.agents.llm_client import LLMClient
        from levelup.tools.base import ToolRegistry
        from levelup.tools.file_read import FileReadTool
        from levelup.tools.file_search import FileSearchTool
        from levelup.tools.file_write import FileWriteTool

        api_key = settings.llm.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        auth_token = None
        if not api_key:
            from levelup.config.auth import get_claude_code_api_key

            claude_code_token = get_claude_code_api_key()
            if claude_code_token:
                auth_token = claude_code_token
            else:
                print_error(
                    "No API key found. Set ANTHROPIC_API_KEY env var or add to config file."
                )
                raise typer.Exit(1)

        llm_client = LLMClient(
            api_key=api_key or settings.llm.api_key,
            auth_token=auth_token or settings.llm.auth_token,
            model=settings.llm.model,
            max_tokens=settings.llm.max_tokens,
            temperature=settings.llm.temperature,
        )
        registry = ToolRegistry()
        registry.register(FileReadTool(path.resolve()))
        registry.register(FileWriteTool(path.resolve()))
        registry.register(FileSearchTool(path.resolve()))
        be = AnthropicSDKBackend(llm_client, registry)

    # Run recon agent
    agent = ReconAgent(
        be,
        path.resolve(),
        language=info.language,
        framework=info.framework,
        test_runner=info.test_runner,
        test_command=info.test_command,
    )

    with console.status("[cyan]Running recon agent..."):
        result = agent.run()

    # Display usage
    table = Table(title="Recon Usage")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Cost", f"${result.cost_usd:.4f}")
    table.add_row("Input tokens", f"{result.input_tokens:,}")
    table.add_row("Output tokens", f"{result.output_tokens:,}")
    table.add_row("Duration", f"{result.duration_ms / 1000:.1f}s")
    table.add_row("Turns", str(result.num_turns))
    console.print(table)

    # Confirm file was written
    from levelup.core.project_context import get_project_context_path

    ctx_path = get_project_context_path(path.resolve())
    if ctx_path.exists():
        console.print(f"\n[bold green]Recon complete.[/bold green] Written to: {ctx_path}")
    else:
        console.print("\n[yellow]Warning: project_context.md was not written by the agent.[/yellow]")


@app.command()
def version() -> None:
    """Show the installed LevelUp version."""
    console.print(get_version_string())


def _get_project_root() -> Path:
    """Return the LevelUp project root (repo root)."""
    return Path(__file__).resolve().parents[3]


INSTALL_META_PATH = Path.home() / ".levelup" / "install.json"


def _load_install_meta() -> dict | None:
    """Load install metadata from ~/.levelup/install.json."""
    if INSTALL_META_PATH.exists():
        import json

        try:
            return json.loads(INSTALL_META_PATH.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _save_install_meta(meta: dict) -> None:
    """Write install metadata to ~/.levelup/install.json."""
    import json

    INSTALL_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    INSTALL_META_PATH.write_text(json.dumps(meta, indent=2))


DEFAULT_REPO_URL = "https://github.com/croxtonveryepic/LevelUp.git"


def _is_levelup_repo(path: Path) -> bool:
    """Check if *path* looks like a LevelUp git checkout."""
    if not (path / ".git").is_dir():
        return False
    pyproject = path / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        text = pyproject.read_text(encoding="utf-8", errors="replace")
        return 'name = "levelup"' in text
    except OSError:
        return False


def _normalize_git_url(url: str) -> str:
    """Convert git SSH URLs to a form usable with ``uv tool install``.

    ``git@host:user/repo.git`` → ``git+ssh://git@host/user/repo.git``
    ``https://…``              → ``git+https://…``
    Already-prefixed URLs are returned as-is.
    """
    url = url.strip()
    if url.startswith("git+"):
        return url
    if url.startswith("git@"):
        # git@github.com:user/repo.git → git+ssh://git@github.com/user/repo.git
        without_prefix = url[len("git@"):]
        host, _, path = without_prefix.partition(":")
        return f"git+ssh://git@{host}/{path}"
    if url.startswith("https://") or url.startswith("http://"):
        return f"git+{url}"
    return url


def _resolve_source(
    *,
    source_flag: Path | None,
    remote_flag: str | None,
    meta: dict,
) -> tuple[Path | None, str | None]:
    """Resolve the update source.

    Returns ``(local_path, remote_url)``.  Exactly one will be non-None.
    """
    method = meta.get("method", "")

    # 1. --remote flag → remote install (no git pull needed)
    if remote_flag:
        return None, _normalize_git_url(remote_flag)

    # 2. --source flag → local path
    if source_flag:
        return source_flag.resolve(), None

    # 3. install.json source_path (if still a valid git repo)
    saved_source = meta.get("source_path")
    if saved_source:
        p = Path(saved_source)
        if p.is_dir() and (p / ".git").is_dir():
            return p, None
        # Source path gone — check for saved repo_url
        repo_url = meta.get("repo_url")
        if repo_url:
            return None, _normalize_git_url(repo_url)

    # 4. Global install with no usable source → default remote
    if method == "global":
        return None, _normalize_git_url(DEFAULT_REPO_URL)

    # 5. CWD is a LevelUp repo
    cwd = Path.cwd()
    if _is_levelup_repo(cwd):
        return cwd, None

    # 6. Ultimate fallback (_get_project_root — works for editable installs)
    return _get_project_root(), None


def _get_uv_bin_exe() -> Path | None:
    """Return the path to ``~/.local/bin/levelup.exe`` if it exists (Windows only)."""
    if sys.platform != "win32":
        return None
    exe = Path.home() / ".local" / "bin" / "levelup.exe"
    return exe if exe.exists() else None


def _unlock_exe_for_update() -> Path | None:
    """On Windows, rename the running ``levelup.exe`` so *uv* can write a new one.

    Returns the ``.old`` path if a rename was performed, else ``None``.
    """
    exe = _get_uv_bin_exe()
    if exe is None:
        return None
    old = exe.with_suffix(".exe.old")
    try:
        # Remove a previous .old file first (may exist from a prior failed cleanup)
        if old.exists():
            old.unlink()
        exe.rename(old)
        return old
    except OSError:
        return None


def _cleanup_old_exe(old_path: Path | None) -> None:
    """Try to delete a ``.old`` exe left by ``_unlock_exe_for_update``.

    Silently ignores errors — the file may still be locked by the
    current process and will be cleaned up on the next update.
    """
    if old_path is None:
        return
    try:
        old_path.unlink()
    except OSError:
        pass


def _cleanup_stale_old_exe() -> None:
    """Remove any leftover ``levelup.exe.old`` from a previous update."""
    if sys.platform != "win32":
        return
    old = Path.home() / ".local" / "bin" / "levelup.exe.old"
    try:
        if old.exists():
            old.unlink()
    except OSError:
        pass


@app.command("self-update")
def self_update(
    source: Optional[Path] = typer.Option(
        None, "--source", help="Path to LevelUp git clone (overrides saved metadata)"
    ),
    remote: Optional[str] = typer.Option(
        None, "--remote", help="Git URL to install from (skips git pull, installs directly)"
    ),
    install_gui: bool = typer.Option(
        False, "--gui", help="Add GUI support (PyQt6) during update"
    ),
) -> None:
    """Pull the latest code and reinstall LevelUp."""
    from datetime import datetime, timezone

    from rich.status import Status

    console.print(f"Current: {get_version_string()}")

    # Clean up stale .old exe from a previous update (Windows)
    _cleanup_stale_old_exe()

    # Load install metadata
    meta = _load_install_meta()
    if meta is None:
        meta = {}
    method = meta.get("method", "")

    # Merge --gui into extras
    if install_gui:
        extras = meta.get("extras", [])
        if "gui" not in extras:
            extras.append("gui")
            meta["extras"] = extras

    # Resolve source (local path or remote URL)
    source_path, remote_url = _resolve_source(
        source_flag=source,
        remote_flag=remote,
        meta=meta,
    )

    if remote_url:
        # ── Remote install path (no git pull) ──────────────────────────────
        extras = meta.get("extras", [])
        if "gui" in extras:
            install_target = f"levelup[gui] @ {remote_url}"
        else:
            install_target = f"levelup @ {remote_url}"

        console.print(f"Source: {remote_url}")
        console.print("[dim]Installing from remote via uv tool...[/dim]")
        old_exe = _unlock_exe_for_update()
        with Status("Installing from remote...", console=console):
            result = subprocess.run(
                ["uv", "tool", "install", "--force", install_target],
                capture_output=True,
                text=True,
            )
        if result.returncode != 0:
            print_error(f"uv tool install failed:\n{result.stderr.strip()}")
            raise typer.Exit(1)
        _cleanup_old_exe(old_exe)

        # Save metadata
        if not meta.get("method"):
            meta["method"] = "global"
        meta["repo_url"] = remote or remote_url
        meta["last_updated"] = datetime.now(timezone.utc).isoformat()
        _save_install_meta(meta)

        console.print(f"[bold green]Updated:[/bold green] {get_version_string()}")
        return

    # ── Local source path ──────────────────────────────────────────────────
    assert source_path is not None

    # Validate source path has .git
    if not source_path.exists():
        print_error(
            f"Source directory not found: {source_path}\n"
            "Re-clone the repository and run the install script, or use:\n"
            "  levelup self-update --source /path/to/LevelUp\n"
            "  levelup self-update --remote https://github.com/croxtonveryepic/LevelUp.git"
        )
        raise typer.Exit(1)

    if not (source_path / ".git").exists():
        print_error(
            f"No git repository at: {source_path}\n"
            "Re-clone the repository and run the install script, or use:\n"
            "  levelup self-update --source /path/to/LevelUp\n"
            "  levelup self-update --remote https://github.com/croxtonveryepic/LevelUp.git"
        )
        raise typer.Exit(1)

    console.print(f"Source: {source_path}")

    # Git pull
    with Status("Pulling latest changes...", console=console):
        result = subprocess.run(
            ["git", "pull"],
            cwd=str(source_path),
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        print_error(f"git pull failed:\n{result.stderr.strip()}")
        raise typer.Exit(1)
    console.print(result.stdout.strip())

    # Reinstall based on method
    if method == "global":
        # Global install via uv tool
        extras = meta.get("extras", [])
        if "gui" in extras:
            install_target = f"{source_path}[gui]"
        else:
            install_target = str(source_path)

        console.print("[dim]Reinstalling via uv tool...[/dim]")
        old_exe = _unlock_exe_for_update()
        with Status("Reinstalling globally...", console=console):
            result = subprocess.run(
                ["uv", "tool", "install", "--force", install_target],
                capture_output=True,
                text=True,
            )
        if result.returncode != 0:
            print_error(f"uv tool install failed:\n{result.stderr.strip()}")
            raise typer.Exit(1)
        _cleanup_old_exe(old_exe)
    else:
        # Editable install (dev mode or fallback)
        extras = meta.get("extras", [])
        install_spec = f".[{','.join(extras)}]" if extras else "."
        console.print("[dim]Reinstalling in editable mode...[/dim]")
        with Status("Reinstalling dependencies...", console=console):
            result = subprocess.run(
                [sys.executable, "-m", "uv", "pip", "install", "-e", install_spec,
                 "--python", sys.executable],
                cwd=str(source_path),
                capture_output=True,
                text=True,
            )
        if result.returncode != 0:
            print_error(f"pip install failed:\n{result.stderr.strip()}")
            raise typer.Exit(1)

    # Update metadata
    if source:
        meta["source_path"] = str(source.resolve())
    if not meta.get("method"):
        meta["method"] = "editable"
    # Auto-detect and save repo_url from git remote
    try:
        remote_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(source_path),
            capture_output=True,
            text=True,
        )
        if remote_result.returncode == 0 and remote_result.stdout.strip():
            meta["repo_url"] = remote_result.stdout.strip()
    except OSError:
        pass
    meta["last_updated"] = datetime.now(timezone.utc).isoformat()
    _save_install_meta(meta)

    console.print(f"[bold green]Updated:[/bold green] {get_version_string()}")


if __name__ == "__main__":
    app()
