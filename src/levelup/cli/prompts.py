"""Interactive prompts: checkpoints, conversations, multi-line input."""

from __future__ import annotations

from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.formatted_text import HTML
from rich.console import Console

from levelup.core.context import CheckpointDecision

console = Console()


def get_task_input() -> tuple[str, str]:
    """Prompt user for task title and description."""
    console.print("\n[bold]Describe your task:[/bold]")
    title = pt_prompt(HTML("<b>Title: </b>"))

    console.print("[dim]Enter description (press Escape then Enter to finish):[/dim]")
    description = pt_prompt(
        HTML("<b>Description: </b>"),
        multiline=True,
    )

    return title.strip(), description.strip()


def get_checkpoint_decision(step_name: str) -> tuple[CheckpointDecision, str]:
    """Present a checkpoint and get user's decision.

    Returns:
        Tuple of (decision, feedback_text).
        feedback_text is non-empty only for REVISE decisions.
    """
    console.print(
        f"\n[bold yellow]--- Checkpoint: {step_name} ---[/bold yellow]"
    )
    console.print(
        "[bold]Choose:[/bold] "
        "[green](a)pprove[/green] | "
        "[yellow](r)evise[/yellow] | "
        "[cyan](i)nstruct[/cyan] | "
        "[red](x) reject[/red]"
    )

    while True:
        choice = pt_prompt(HTML("<b>> </b>")).strip().lower()
        if choice in ("a", "approve"):
            return CheckpointDecision.APPROVE, ""
        elif choice in ("r", "revise"):
            console.print("[dim]Enter revision feedback (Escape then Enter to finish):[/dim]")
            feedback = pt_prompt(
                HTML("<b>Feedback: </b>"),
                multiline=True,
            )
            return CheckpointDecision.REVISE, feedback.strip()
        elif choice in ("i", "instruct"):
            console.print("[dim]Enter project rule (Escape then Enter to finish):[/dim]")
            instruction = pt_prompt(
                HTML("<b>Rule: </b>"),
                multiline=True,
            )
            return CheckpointDecision.INSTRUCT, instruction.strip()
        elif choice in ("x", "reject"):
            return CheckpointDecision.REJECT, ""
        else:
            console.print("[dim]Please enter a, r, i, or x[/dim]")


def get_conversation_reply(agent_message: str) -> str:
    """Show an agent's message and get user's reply for interactive agents."""
    console.print(f"\n[bold blue]Agent:[/bold blue] {agent_message}")
    reply = pt_prompt(HTML("<b>You: </b>"))
    return reply.strip()


def pick_resumable_run(runs: list) -> object:
    """Display resumable runs and let the user pick one.

    Args:
        runs: List of RunRecord objects (must be non-empty).

    Returns:
        The selected RunRecord.
    """
    from rich.table import Table

    table = Table(title="Resumable Runs", show_lines=False)
    table.add_column("#", style="bold", width=4)
    table.add_column("Run ID", style="cyan", width=10)
    table.add_column("Task", style="white")
    table.add_column("Step", style="yellow", width=14)
    table.add_column("Status", style="red", width=10)
    table.add_column("Updated", style="dim", width=20)

    for i, run in enumerate(runs, 1):
        table.add_row(
            str(i),
            run.run_id[:8],
            run.task_title or "(untitled)",
            run.current_step or "—",
            run.status,
            run.updated_at[:19].replace("T", " "),
        )

    console.print(table)
    console.print("[dim]Enter a number to select a run, or 'q' to quit.[/dim]")

    while True:
        choice = pt_prompt(HTML("<b>> </b>")).strip().lower()
        if choice in ("q", "quit"):
            raise KeyboardInterrupt
        try:
            idx = int(choice)
        except ValueError:
            console.print(f"[dim]Please enter a number 1-{len(runs)}, or 'q'[/dim]")
            continue
        if 1 <= idx <= len(runs):
            return runs[idx - 1]
        console.print(f"[dim]Please enter a number 1-{len(runs)}, or 'q'[/dim]")


def confirm_action(message: str, default: bool = True) -> bool:
    """Ask user for a yes/no confirmation."""
    suffix = "[Y/n]" if default else "[y/N]"
    console.print(f"{message} {suffix}")
    choice = pt_prompt(HTML("<b>> </b>")).strip().lower()
    if not choice:
        return default
    return choice in ("y", "yes")
