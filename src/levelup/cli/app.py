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
    table.add_column("Cost", justify="right")
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
    run_id: str = typer.Argument(..., help="Run ID to resume"),
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

    # Look up run
    record = state_manager.get_run(run_id)
    if record is None:
        print_error(f"Run '{run_id}' not found.")
        raise typer.Exit(1)

    if record.status not in ("failed", "aborted"):
        print_error(f"Run '{run_id}' has status '{record.status}' — only failed or aborted runs can be resumed.")
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

        project_path = ctx.project_path
        repo = git.Repo(str(project_path))

        # Warn if not on expected branch
        branch_name = f"levelup/{ctx.run_id}"
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


@app.command("self-update")
def self_update() -> None:
    """Pull the latest code and reinstall LevelUp."""
    from rich.status import Status

    console.print(f"Current: {get_version_string()}")

    project_root = _get_project_root()
    if not (project_root / ".git").exists():
        print_error("Not a git repository — cannot self-update.")
        raise typer.Exit(1)

    with Status("Pulling latest changes...", console=console):
        result = subprocess.run(
            ["git", "pull"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        print_error(f"git pull failed:\n{result.stderr.strip()}")
        raise typer.Exit(1)
    console.print(result.stdout.strip())

    with Status("Reinstalling dependencies...", console=console):
        result = subprocess.run(
            [sys.executable, "-m", "uv", "pip", "install", "-e", ".",
             "--python", sys.executable],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        print_error(f"pip install failed:\n{result.stderr.strip()}")
        raise typer.Exit(1)

    console.print(f"[bold green]Updated:[/bold green] {get_version_string()}")


if __name__ == "__main__":
    app()
