"""TicketSource ABC and Ticket model."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from levelup.core.context import TaskInput


class Ticket(BaseModel):
    """A ticket from an external source."""

    id: str
    title: str
    description: str = ""
    source: str = "unknown"
    url: str | None = None
    labels: list[str] = []


class TicketSource(ABC):
    """Abstract base class for ticket sources."""

    name: str

    @abstractmethod
    def get_task(self, ticket_id: str | None = None) -> TaskInput:
        """Retrieve a task from this source."""

    @abstractmethod
    def update_status(self, ticket_id: str, status: str) -> None:
        """Update the status of a ticket in the source system."""
