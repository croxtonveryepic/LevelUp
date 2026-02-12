"""Tests for updating the existing cost tracking test to reflect new behavior."""

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


class TestCostUsdCalculatedFromTokens:
    """Test that replaces test_cost_usd_defaults_to_zero with new behavior."""

    def test_cost_usd_calculated_from_token_counts(self):
        """AnthropicSDKBackend should calculate cost_usd from token counts, not default to zero.

        This test replaces the original test_cost_usd_defaults_to_zero test in test_cost_tracking.py.

        The original test expected:
            result.cost_usd == 0.0

        The new behavior should calculate cost from token usage:
            input_tokens=100, output_tokens=50
            Using Sonnet pricing ($3/M input, $15/M output):
            cost = (100 * 3 + 50 * 15) / 1_000_000 = $0.00105
        """
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="ok",
            input_tokens=100,
            output_tokens=50,
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

        # NEW BEHAVIOR: Cost should be calculated from token usage
        # Input: 100 * ($3.00 / 1M) = $0.0003
        # Output: 50 * ($15.00 / 1M) = $0.00075
        # Total: $0.00105
        assert result.cost_usd == pytest.approx(0.00105, abs=0.000001)

        # OLD BEHAVIOR (to be removed):
        # assert result.cost_usd == 0.0

    def test_existing_test_location_and_name(self):
        """Document the location of the test that needs to be updated."""
        from pathlib import Path

        # The test to update is in test_cost_tracking.py
        test_file = Path(__file__).parent / "test_cost_tracking.py"
        assert test_file.exists()

        content = test_file.read_text(encoding="utf-8")

        # The test is in TestAnthropicSDKBackendTokenFields class
        assert "class TestAnthropicSDKBackendTokenFields" in content

        # The test method is test_cost_usd_defaults_to_zero
        assert "def test_cost_usd_defaults_to_zero" in content

        # It's around line 270
        lines = content.splitlines()
        for i, line in enumerate(lines, start=1):
            if "def test_cost_usd_defaults_to_zero" in line:
                # Found it - document the line number
                assert 260 <= i <= 280, f"Test found at line {i}, expected around line 270"
                break

    def test_original_test_assertion_to_change(self):
        """Document the exact assertion that needs to be changed."""
        from pathlib import Path

        test_file = Path(__file__).parent / "test_cost_tracking.py"
        content = test_file.read_text(encoding="utf-8")

        # The original assertion is: assert result.cost_usd == 0.0
        assert "assert result.cost_usd == 0.0" in content

        # After implementation, this should become:
        # assert result.cost_usd == pytest.approx(0.00105, abs=0.000001)

    def test_original_test_docstring_to_update(self):
        """Document the docstring that needs to be updated."""
        from pathlib import Path

        test_file = Path(__file__).parent / "test_cost_tracking.py"
        content = test_file.read_text(encoding="utf-8")

        # The original docstring says cost_usd comes from token counts
        # But it expects zero, which is contradictory
        # Find the docstring
        lines = content.splitlines()
        in_test = False
        for line in lines:
            if "def test_cost_usd_defaults_to_zero" in line:
                in_test = True
            if in_test and '"""' in line:
                # Found the docstring
                assert "does not set cost_usd" in line or "comes from token counts" in line
                break

        # The docstring should be updated to reflect the new behavior


class TestExistingTestTokenValues:
    """Verify the token values used in the existing test."""

    def test_token_values_in_existing_test(self):
        """Document the token values used in test_cost_usd_defaults_to_zero."""
        from pathlib import Path

        test_file = Path(__file__).parent / "test_cost_tracking.py"
        content = test_file.read_text(encoding="utf-8")

        # Extract the test function
        lines = content.splitlines()
        in_test = False
        test_lines = []
        for line in lines:
            if "def test_cost_usd_defaults_to_zero" in line:
                in_test = True
            if in_test:
                test_lines.append(line)
                if line.strip().startswith("assert result.cost_usd"):
                    break

        test_code = "\n".join(test_lines)

        # The test uses input_tokens=100, output_tokens=50
        assert "input_tokens=100" in test_code
        assert "output_tokens=50" in test_code

        # Calculate expected cost with these values
        # Sonnet pricing: $3/M input, $15/M output
        expected_cost = (100 * 3.00 + 50 * 15.00) / 1_000_000
        assert expected_cost == pytest.approx(0.00105, abs=0.000001)


class TestUpdatedTestBehavior:
    """Test the new expected behavior after updating the existing test."""

    def test_new_behavior_with_original_test_values(self):
        """Verify the new calculation matches the expected cost."""
        # Original test values
        input_tokens = 100
        output_tokens = 50

        # Sonnet pricing
        input_price_per_million = 3.00
        output_price_per_million = 15.00

        # Calculate cost
        cost_usd = (
            (input_tokens / 1_000_000 * input_price_per_million) +
            (output_tokens / 1_000_000 * output_price_per_million)
        )

        # Expected value
        assert cost_usd == pytest.approx(0.00105, abs=0.000001)

    def test_new_test_should_pass_after_implementation(self):
        """After implementation, the updated test should pass with calculated cost."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm._model = "claude-sonnet-4-5-20250929"
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="ok",
            input_tokens=100,
            output_tokens=50,
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

        # After implementation, this should pass
        # Currently will fail because cost calculation is not implemented
        assert result.cost_usd == pytest.approx(0.00105, abs=0.000001)
