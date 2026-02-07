"""BaseAgent abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from levelup.agents.backend import AgentResult, Backend
from levelup.core.context import PipelineContext


class BaseAgent(ABC):
    """Abstract base class for all LevelUp agents."""

    name: str
    description: str

    def __init__(self, backend: Backend, project_path: Path) -> None:
        self.backend = backend
        self.project_path = project_path

    @abstractmethod
    def get_system_prompt(self, ctx: PipelineContext) -> str:
        """Return the system prompt for this agent, potentially using context."""

    @abstractmethod
    def get_allowed_tools(self) -> list[str]:
        """Return the list of tool names this agent is allowed to use."""

    @abstractmethod
    def run(self, ctx: PipelineContext) -> tuple[PipelineContext, AgentResult]:
        """Execute this agent's work and return updated context plus usage metrics."""
