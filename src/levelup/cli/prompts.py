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
        elif choice in ("x", "reject"):
            return CheckpointDecision.REJECT, ""
        else:
            console.print("[dim]Please enter a, r, or x[/dim]")


def get_conversation_reply(agent_message: str) -> str:
    """Show an agent's message and get user's reply for interactive agents."""
    console.print(f"\n[bold blue]Agent:[/bold blue] {agent_message}")
    reply = pt_prompt(HTML("<b>You: </b>"))
    return reply.strip()


def confirm_action(message: str, default: bool = True) -> bool:
    """Ask user for a yes/no confirmation."""
    suffix = "[Y/n]" if default else "[y/N]"
    console.print(f"{message} {suffix}")
    choice = pt_prompt(HTML("<b>> </b>")).strip().lower()
    if not choice:
        return default
    return choice in ("y", "yes")
