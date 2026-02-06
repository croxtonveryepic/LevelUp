"""BaseTool ABC and ToolRegistry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for all LevelUp tools."""

    name: str
    description: str

    @abstractmethod
    def get_input_schema(self) -> dict[str, Any]:
        """Return JSON Schema for tool input parameters."""

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """Execute the tool and return a string result."""

    def to_anthropic_schema(self) -> dict[str, Any]:
        """Convert to Anthropic API tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.get_input_schema(),
        }


class ToolRegistry:
    """Registry that holds available tools and provides lookup."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool by name."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """Get a tool by name. Raises KeyError if not found."""
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def get_tools(self, names: list[str] | None = None) -> list[BaseTool]:
        """Get multiple tools by name, or all if names is None."""
        if names is None:
            return list(self._tools.values())
        return [self.get(n) for n in names]

    def get_anthropic_schemas(self, names: list[str] | None = None) -> list[dict[str, Any]]:
        """Get Anthropic API tool schemas for the specified tools."""
        return [t.to_anthropic_schema() for t in self.get_tools(names)]

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())
