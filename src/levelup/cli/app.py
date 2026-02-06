"""Typer CLI commands: run, detect, config, gui, status."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer

from levelup.cli.display import (
    console,
    print_banner,
    print_error,
    print_project_info,
)

app = typer.Typer(
    name="levelup",
    help="AI-Powered TDD Development Tool",
    no_args_is_help=True,
)


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
    db_path: Optional[Path] = typer.Option(
        None, "--db-path", help="Override state DB path (default: ~/.levelup/state.db)"
    ),
    backend: Optional[str] = typer.Option(
        None, "--backend", help="Backend: 'claude_code' (default) or 'anthropic_sdk'"
    ),
) -> None:
    """Run the LevelUp TDD pipeline on a task."""
    from levelup.cli.prompts import get_task_input
    from levelup.config.loader import load_settings
    from levelup.core.context import PipelineContext, TaskInput
    from levelup.core.orchestrator import Orchestrator
    from levelup.state.manager import StateManager

    if not headless:
        print_banner()

    # Headless mode requires a task
    if headless and not task:
        print_error("--headless requires a task argument (can't prompt interactively).")
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
    if task:
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
    )
    ctx = orchestrator.run(task_input)

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

    console.print(f"\n[bold]Ticket source:[/bold] {settings.ticket_source}")


@app.command()
def gui(
    db_path: Optional[Path] = typer.Option(
        None, "--db-path", help="Override state DB path"
    ),
) -> None:
    """Launch the LevelUp GUI dashboard."""
    try:
        from levelup.gui.app import launch_gui
    except ImportError:
        print_error(
            "PyQt6 is not installed. Install with: "
            'pip install "levelup[gui]"'
        )
        raise typer.Exit(1)

    launch_gui(db_path=db_path)


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
    table.add_column("Started")

    status_styles = {
        "running": "blue",
        "waiting_for_input": "yellow",
        "completed": "green",
        "failed": "red",
        "aborted": "dim",
        "pending": "dim",
    }

    for r in runs:
        style = status_styles.get(r.status, "")
        status_display = f"[{style}]{r.status}[/{style}]" if style else r.status
        table.add_row(
            r.run_id[:12],
            r.task_title,
            r.project_path,
            status_display,
            r.current_step or "",
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


if __name__ == "__main__":
    app()
