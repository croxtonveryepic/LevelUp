"""Backend abstraction: ClaudeCodeBackend and AnthropicSDKBackend."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from levelup.agents.claude_code_client import ClaudeCodeClient
from levelup.agents.llm_client import LLMClient
from levelup.tools.base import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result from running an agent, including usage metrics."""

    text: str = ""
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: float = 0.0
    num_turns: int = 0

# Mapping from Claude Code tool names to LevelUp tool names
_CLAUDE_TO_LEVELUP: dict[str, list[str]] = {
    "Read": ["file_read"],
    "Write": ["file_write"],
    "Edit": ["file_write"],
    "Glob": ["file_search"],
    "Grep": ["file_search"],
    "Bash": ["shell", "test_runner"],
}


@runtime_checkable
class Backend(Protocol):
    """Protocol for agent execution backends."""

    def run_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        allowed_tools: list[str],
        working_directory: str,
    ) -> AgentResult:
        """Run an agent and return its result with usage metrics.

        Args:
            system_prompt: The system prompt for the agent.
            user_prompt: The user prompt / task.
            allowed_tools: List of tool names the agent may use.
            working_directory: Working directory for sandboxing.

        Returns:
            AgentResult with text response and usage metrics.
        """
        ...


class ClaudeCodeBackend:
    """Backend that spawns `claude -p` subprocesses."""

    def __init__(self, client: ClaudeCodeClient) -> None:
        self._client = client

    def run_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        allowed_tools: list[str],
        working_directory: str,
    ) -> AgentResult:
        result = self._client.run(
            prompt=user_prompt,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            working_directory=working_directory,
        )
        return AgentResult(
            text=result.text,
            cost_usd=result.cost_usd,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            duration_ms=result.duration_ms,
            num_turns=result.num_turns,
        )


class AnthropicSDKBackend:
    """Backend that wraps the existing LLMClient + ToolRegistry."""

    def __init__(self, llm_client: LLMClient, tool_registry: ToolRegistry) -> None:
        self._llm_client = llm_client
        self._tool_registry = tool_registry

    @property
    def llm_client(self) -> LLMClient:
        return self._llm_client

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._tool_registry

    def run_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        allowed_tools: list[str],
        working_directory: str,
    ) -> AgentResult:
        # Map Claude Code tool names to LevelUp tool names
        levelup_tools = self._map_tool_names(allowed_tools)

        # Get only tools that exist in the registry
        available = [t for t in levelup_tools if t in self._tool_registry.tool_names]
        tools = self._tool_registry.get_anthropic_schemas(available)

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_prompt},
        ]

        loop_result = self._llm_client.run_tool_loop(
            system=system_prompt,
            messages=messages,
            tools=tools,
            tool_registry=self._tool_registry,
        )
        return AgentResult(
            text=loop_result.text,
            input_tokens=loop_result.input_tokens,
            output_tokens=loop_result.output_tokens,
            num_turns=loop_result.num_turns,
        )

    def _map_tool_names(self, claude_code_names: list[str]) -> list[str]:
        """Map Claude Code tool names back to LevelUp tool names."""
        result: list[str] = []
        for name in claude_code_names:
            mapped = _CLAUDE_TO_LEVELUP.get(name, [])
            for tool_name in mapped:
                if tool_name not in result:
                    result.append(tool_name)
        return result
