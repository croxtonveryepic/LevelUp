"""Anthropic API wrapper with tool-use loop support."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import anthropic

from levelup.tools.base import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class ToolLoopResult:
    """Result from a tool-use loop, including token usage."""

    text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    num_turns: int = 0

DEFAULT_MAX_TOKENS = 8192
MAX_TOOL_ITERATIONS = 50


class LLMClient:
    """Thin wrapper around the Anthropic SDK."""

    def __init__(
        self,
        api_key: str = "",
        auth_token: str = "",
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = 0.0,
    ) -> None:
        self._client = anthropic.Anthropic(
            api_key=api_key or None,
            auth_token=auth_token or None,
        )
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    def structured_call(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Make a single API call and return the text response."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self._client.messages.create(**kwargs)

        # Extract text blocks
        text_parts: list[str] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)

        return "\n".join(text_parts)

    def run_tool_loop(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_registry: ToolRegistry,
        on_tool_call: Any | None = None,
    ) -> ToolLoopResult:
        """Run a tool-use conversation loop until the model produces a final text response.

        Args:
            system: System prompt.
            messages: Initial messages.
            tools: Anthropic tool schemas.
            tool_registry: Registry to execute tool calls.
            on_tool_call: Optional callback(tool_name, tool_input, result) for progress display.

        Returns:
            ToolLoopResult with final text and accumulated token usage.
        """
        conversation = list(messages)
        total_input_tokens = 0
        total_output_tokens = 0
        num_turns = 0

        for _iteration in range(MAX_TOOL_ITERATIONS):
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=system,
                messages=conversation,
                tools=tools,
            )
            num_turns += 1

            # Accumulate token usage
            usage = getattr(response, "usage", None)
            if usage:
                total_input_tokens += getattr(usage, "input_tokens", 0)
                total_output_tokens += getattr(usage, "output_tokens", 0)

            # Check if the response contains tool use
            has_tool_use = any(block.type == "tool_use" for block in response.content)

            if not has_tool_use:
                # Final text response
                text_parts = [block.text for block in response.content if block.type == "text"]
                return ToolLoopResult(
                    text="\n".join(text_parts),
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    num_turns=num_turns,
                )

            # Process tool calls
            assistant_content: list[dict[str, Any]] = []
            tool_results: list[dict[str, Any]] = []

            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

                    # Execute the tool
                    try:
                        tool = tool_registry.get(block.name)
                        result = tool.execute(**block.input)
                    except KeyError:
                        result = f"Error: unknown tool '{block.name}'"
                    except Exception as e:
                        result = f"Error executing {block.name}: {e}"

                    if on_tool_call:
                        on_tool_call(block.name, block.input, result)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Add assistant message and tool results to conversation
            conversation.append({"role": "assistant", "content": assistant_content})
            conversation.append({"role": "user", "content": tool_results})

        return ToolLoopResult(
            text="Error: tool loop exceeded maximum iterations",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            num_turns=num_turns,
        )
