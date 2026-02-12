"""Tests for cost calculation in AnthropicSDKBackend."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from levelup.agents.backend import AnthropicSDKBackend
from levelup.agents.llm_client import LLMClient, ToolLoopResult
from levelup.tools.base import BaseTool, ToolRegistry


class _StubTool(BaseTool):
    """Minimal tool for testing ToolRegistry interactions."""

    name = "file_read"
    description = "Read a file"

    def get_input_schema(self):
        return {"type": "object", "properties": {"path": {"type": "string"}}}

    def execute(self, **kwargs):
        return "file contents"


class TestAnthropicSDKBackendCostCalculation:
    """AnthropicSDKBackend should calculate cost_usd from token counts using Anthropic pricing."""

    def test_calculates_cost_for_sonnet_model(self):
        """Cost should be calculated for claude-sonnet-4-5-20250929 using standard pricing."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="response",
            input_tokens=100000,  # 100K input tokens
            output_tokens=50000,   # 50K output tokens
            num_turns=1,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="do work",
            allowed_tools=["Read"],
            working_directory="/tmp/proj",
        )

        # Input: 100K * ($3.00 / 1M) = $0.30
        # Output: 50K * ($15.00 / 1M) = $0.75
        # Total: $1.05
        assert result.cost_usd == pytest.approx(1.05, abs=0.001)

    def test_calculates_cost_for_opus_model(self):
        """Cost should be calculated for claude-opus-4-6 using its pricing."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-opus-4-6"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="response",
            input_tokens=100000,  # 100K input tokens
            output_tokens=50000,   # 50K output tokens
            num_turns=1,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="do work",
            allowed_tools=["Read"],
            working_directory="/tmp/proj",
        )

        # Input: 100K * ($5.00 / 1M) = $0.50
        # Output: 50K * ($25.00 / 1M) = $1.25
        # Total: $1.75
        assert result.cost_usd == pytest.approx(1.75, abs=0.001)

    def test_calculates_cost_for_haiku_model(self):
        """Cost should be calculated for haiku model using its pricing."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-3-5-haiku-20241022"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="response",
            input_tokens=100000,  # 100K input tokens
            output_tokens=50000,   # 50K output tokens
            num_turns=1,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="do work",
            allowed_tools=["Read"],
            working_directory="/tmp/proj",
        )

        # Input: 100K * ($1.00 / 1M) = $0.10
        # Output: 50K * ($5.00 / 1M) = $0.25
        # Total: $0.35
        assert result.cost_usd == pytest.approx(0.35, abs=0.001)

    def test_cost_is_zero_when_no_tokens_consumed(self):
        """Cost should be zero when no tokens are consumed."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="ok",
            input_tokens=0,
            output_tokens=0,
            num_turns=1,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="s",
            user_prompt="u",
            allowed_tools=["Read"],
            working_directory="/tmp",
        )

        assert result.cost_usd == 0.0

    def test_cost_with_small_token_counts(self):
        """Cost should be calculated correctly for small token counts."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="response",
            input_tokens=500,
            output_tokens=200,
            num_turns=1,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="do work",
            allowed_tools=["Read"],
            working_directory="/tmp/proj",
        )

        # Input: 500 * ($3.00 / 1M) = $0.0015
        # Output: 200 * ($15.00 / 1M) = $0.0030
        # Total: $0.0045
        assert result.cost_usd == pytest.approx(0.0045, abs=0.00001)

    def test_cost_with_only_input_tokens(self):
        """Cost should be calculated when only input tokens are consumed."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="response",
            input_tokens=1000,
            output_tokens=0,
            num_turns=1,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="do work",
            allowed_tools=["Read"],
            working_directory="/tmp/proj",
        )

        # Input: 1000 * ($3.00 / 1M) = $0.0030
        # Output: 0
        # Total: $0.0030
        assert result.cost_usd == pytest.approx(0.0030, abs=0.00001)

    def test_cost_with_only_output_tokens(self):
        """Cost should be calculated when only output tokens are consumed."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="response",
            input_tokens=0,
            output_tokens=500,
            num_turns=1,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="do work",
            allowed_tools=["Read"],
            working_directory="/tmp/proj",
        )

        # Input: 0
        # Output: 500 * ($15.00 / 1M) = $0.0075
        # Total: $0.0075
        assert result.cost_usd == pytest.approx(0.0075, abs=0.00001)

    def test_cost_for_unknown_model_defaults_to_sonnet_pricing(self):
        """Cost should use sonnet pricing as fallback for unknown models."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "unknown-model-xyz"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="response",
            input_tokens=100000,
            output_tokens=50000,
            num_turns=1,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="do work",
            allowed_tools=["Read"],
            working_directory="/tmp/proj",
        )

        # Should default to Sonnet pricing:
        # Input: 100K * ($3.00 / 1M) = $0.30
        # Output: 50K * ($15.00 / 1M) = $0.75
        # Total: $1.05
        assert result.cost_usd == pytest.approx(1.05, abs=0.001)

    def test_cost_calculation_with_large_token_counts(self):
        """Cost should be calculated correctly for large token counts."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="response",
            input_tokens=1000000,  # 1M input tokens
            output_tokens=500000,   # 500K output tokens
            num_turns=5,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="do work",
            allowed_tools=["Read"],
            working_directory="/tmp/proj",
        )

        # Input: 1M * ($3.00 / 1M) = $3.00
        # Output: 500K * ($15.00 / 1M) = $7.50
        # Total: $10.50
        assert result.cost_usd == pytest.approx(10.50, abs=0.01)

    def test_token_counts_are_preserved(self):
        """Token counts from LLMClient should be preserved in AgentResult."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="resp",
            input_tokens=1234,
            output_tokens=5678,
            num_turns=3,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="do work",
            allowed_tools=["Read"],
            working_directory="/tmp/proj",
        )

        assert result.input_tokens == 1234
        assert result.output_tokens == 5678
        assert result.num_turns == 3


class TestAnthropicPricingConstants:
    """Tests for the pricing constants that should be added to backend.py."""

    def test_pricing_constants_exist(self):
        """ANTHROPIC_PRICING constant should exist in backend module."""
        from levelup.agents import backend

        # This test will fail initially - pricing constant needs to be added
        assert hasattr(backend, "ANTHROPIC_PRICING")

    def test_pricing_has_all_models(self):
        """ANTHROPIC_PRICING should include all supported models."""
        from levelup.agents.backend import ANTHROPIC_PRICING

        # Should have entries for Sonnet, Opus, and Haiku
        assert "claude-sonnet-4-5-20250929" in ANTHROPIC_PRICING
        assert "claude-opus-4-6" in ANTHROPIC_PRICING
        assert "claude-3-5-haiku-20241022" in ANTHROPIC_PRICING

    def test_sonnet_pricing_values(self):
        """Sonnet pricing should match Anthropic API pricing."""
        from levelup.agents.backend import ANTHROPIC_PRICING

        sonnet = ANTHROPIC_PRICING["claude-sonnet-4-5-20250929"]
        assert sonnet["input"] == 3.00  # $3.00 per million tokens
        assert sonnet["output"] == 15.00  # $15.00 per million tokens

    def test_opus_pricing_values(self):
        """Opus pricing should match Anthropic API pricing."""
        from levelup.agents.backend import ANTHROPIC_PRICING

        opus = ANTHROPIC_PRICING["claude-opus-4-6"]
        assert opus["input"] == 5.00  # $5.00 per million tokens
        assert opus["output"] == 25.00  # $25.00 per million tokens

    def test_haiku_pricing_values(self):
        """Haiku pricing should match Anthropic API pricing."""
        from levelup.agents.backend import ANTHROPIC_PRICING

        haiku = ANTHROPIC_PRICING["claude-3-5-haiku-20241022"]
        assert haiku["input"] == 1.00  # $1.00 per million tokens
        assert haiku["output"] == 5.00  # $5.00 per million tokens


class TestCalculateCostMethod:
    """Tests for the _calculate_cost helper method in AnthropicSDKBackend."""

    def test_calculate_cost_method_exists(self):
        """AnthropicSDKBackend should have _calculate_cost method."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        registry = ToolRegistry()

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)

        # This test will fail initially - method needs to be added
        assert hasattr(backend, "_calculate_cost")
        assert callable(backend._calculate_cost)

    def test_calculate_cost_returns_float(self):
        """_calculate_cost should return a float value."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        registry = ToolRegistry()

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)

        cost = backend._calculate_cost(input_tokens=1000, output_tokens=500)
        assert isinstance(cost, float)

    def test_calculate_cost_with_zero_tokens(self):
        """_calculate_cost should return 0.0 for zero tokens."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        registry = ToolRegistry()

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)

        cost = backend._calculate_cost(input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_calculate_cost_uses_model_from_llm_client(self):
        """_calculate_cost should use the model from self._llm_client._model."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-opus-4-6"
        registry = ToolRegistry()

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)

        # Should use Opus pricing
        cost = backend._calculate_cost(input_tokens=100000, output_tokens=50000)
        # Input: 100K * ($5.00 / 1M) = $0.50
        # Output: 50K * ($25.00 / 1M) = $1.25
        # Total: $1.75
        assert cost == pytest.approx(1.75, abs=0.001)
