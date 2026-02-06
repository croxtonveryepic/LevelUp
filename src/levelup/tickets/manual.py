"""ManualTicketSource - gets task from direct user input (MVP)."""

from __future__ import annotations

from levelup.cli.prompts import get_task_input
from levelup.core.context import TaskInput
from levelup.tickets.base import TicketSource


class ManualTicketSource(TicketSource):
    """Gets tasks from direct user input via CLI prompts."""

    name = "manual"

    def get_task(self, ticket_id: str | None = None) -> TaskInput:
        """Prompt user for task input."""
        title, description = get_task_input()
        return TaskInput(
            title=title,
            description=description,
            source="manual",
        )

    def update_status(self, ticket_id: str, status: str) -> None:
        """No-op for manual tickets."""
