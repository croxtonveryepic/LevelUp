"""Backend abstraction: ClaudeCodeBackend and AnthropicSDKBackend."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from levelup.agents.claude_code_client import ClaudeCodeClient
from levelup.agents.llm_client import LLMClient
from levelup.tools.base import ToolRegistry

logger = logging.getLogger(__name__)


# Anthropic API pricing per million tokens (USD)
ANTHROPIC_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5-20250929": {
        "input": 3.00,
        "output": 15.00,
    },
    "claude-opus-4-6": {
        "input": 5.00,
        "output": 25.00,
    },
    "claude-3-5-haiku-20241022": {
        "input": 1.00,
        "output": 5.00,
    },
}


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
        *,
        thinking_budget: int | None = None,
    ) -> AgentResult:
        """Run an agent and return its result with usage metrics.

        Args:
            system_prompt: The system prompt for the agent.
            user_prompt: The user prompt / task.
            allowed_tools: List of tool names the agent may use.
            working_directory: Working directory for sandboxing.
            thinking_budget: Optional extended thinking budget in tokens.

        Returns:
            AgentResult with text response and usage metrics.
        """
        ...


class ClaudeCodeBackend:
    """Backend that spawns `claude -p` subprocesses."""

    def __init__(self, client: ClaudeCodeClient, *, thinking_budget: int | None = None) -> None:
        self._client = client
        self._thinking_budget = thinking_budget

    def run_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        allowed_tools: list[str],
        working_directory: str,
        *,
        thinking_budget: int | None = None,
    ) -> AgentResult:
        effective = thinking_budget if thinking_budget is not None else self._thinking_budget
        result = self._client.run(
            prompt=user_prompt,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            working_directory=working_directory,
            thinking_budget=effective,
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

    def __init__(self, llm_client: LLMClient, tool_registry: ToolRegistry, *, thinking_budget: int | None = None) -> None:
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._thinking_budget = thinking_budget

    @property
    def llm_client(self) -> LLMClient:
        return self._llm_client

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._tool_registry

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD based on token usage.

        Args:
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens consumed.

        Returns:
            Cost in USD.
        """
        # Get model-specific pricing, default to Sonnet if model not found
        model = self._llm_client._model
        pricing = ANTHROPIC_PRICING.get(model, ANTHROPIC_PRICING["claude-sonnet-4-5-20250929"])

        # Calculate cost: (tokens / 1M) * price_per_million
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def run_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        allowed_tools: list[str],
        working_directory: str,
        *,
        thinking_budget: int | None = None,
    ) -> AgentResult:
        effective = thinking_budget if thinking_budget is not None else self._thinking_budget
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
            thinking_budget=effective,
        )

        # Calculate cost from token usage
        cost_usd = self._calculate_cost(loop_result.input_tokens, loop_result.output_tokens)

        return AgentResult(
            text=loop_result.text,
            cost_usd=cost_usd,
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
