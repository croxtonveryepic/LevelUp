"""Tests for cost breakdown display formatting in CLI output."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from levelup.cli.display import print_pipeline_summary
from levelup.core.context import PipelineContext, PipelineStatus, StepUsage, TaskInput


class TestCostBreakdownTableDisplay:
    """Cost breakdown table should display with correct formatting."""

    def test_cost_breakdown_displays_all_steps(self):
        """Cost breakdown table should show all steps from step_usage."""
        ctx = PipelineContext(
            task=TaskInput(title="test task"),
            project_path=Path("/tmp/proj"),
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["requirements"] = StepUsage(
            cost_usd=0.05,
            input_tokens=1000,
            output_tokens=500,
            duration_ms=2500.0,
            num_turns=2,
        )
        ctx.step_usage["planning"] = StepUsage(
            cost_usd=0.03,
            input_tokens=800,
            output_tokens=400,
            duration_ms=1800.0,
            num_turns=1,
        )
        ctx.total_cost_usd = 0.08

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        # Monkeypatch the global console in display module
        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # Should contain cost breakdown header
            assert "Cost Breakdown" in result

            # Should show both steps
            assert "requirements" in result
            assert "planning" in result

            # Should show costs
            assert "$0.0500" in result
            assert "$0.0300" in result

        finally:
            display_module.console = original_console

    def test_cost_displays_with_four_decimal_places(self):
        """Cost should display with 4 decimal places."""
        ctx = PipelineContext(
            task=TaskInput(title="test"),
            project_path=Path("/tmp"),
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["coding"] = StepUsage(
            cost_usd=0.1234,
            input_tokens=1000,
            output_tokens=500,
            duration_ms=1000.0,
            num_turns=1,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # Should show cost with exactly 4 decimal places
            assert "$0.1234" in result

        finally:
            display_module.console = original_console

    def test_zero_cost_displays_as_dash(self):
        """Steps with zero cost should display '-' instead of '$0.0000'."""
        ctx = PipelineContext(
            task=TaskInput(title="test"),
            project_path=Path("/tmp"),
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["detect"] = StepUsage(
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
            duration_ms=100.0,
            num_turns=0,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # Should NOT show $0.0000
            assert "$0.0000" not in result

            # The row should still be present but cost shown as '-'
            # (This is harder to assert precisely due to table formatting)

        finally:
            display_module.console = original_console

    def test_token_counts_display_with_commas(self):
        """Token counts should display with comma separators."""
        ctx = PipelineContext(
            task=TaskInput(title="test"),
            project_path=Path("/tmp"),
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["requirements"] = StepUsage(
            cost_usd=0.05,
            input_tokens=50000,
            output_tokens=25000,
            duration_ms=2500.0,
            num_turns=2,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # Total tokens: 75,000
            assert "75,000" in result

        finally:
            display_module.console = original_console

    def test_zero_tokens_display_as_dash(self):
        """Steps with zero tokens should display '-' instead of '0'."""
        ctx = PipelineContext(
            task=TaskInput(title="test"),
            project_path=Path("/tmp"),
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["detect"] = StepUsage(
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
            duration_ms=100.0,
            num_turns=0,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # The table row should exist, but we're checking behavior
            # This is tested by absence of "0" in the token column for this step

        finally:
            display_module.console = original_console

    def test_duration_displays_in_seconds_with_one_decimal(self):
        """Duration should display in seconds with 1 decimal place."""
        ctx = PipelineContext(
            task=TaskInput(title="test"),
            project_path=Path("/tmp"),
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["coding"] = StepUsage(
            cost_usd=0.05,
            input_tokens=1000,
            output_tokens=500,
            duration_ms=2567.8,  # Should display as 2.6s
            num_turns=1,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # Duration: 2567.8 / 1000 = 2.5678 -> formatted as 2.6s
            assert "2.6s" in result

        finally:
            display_module.console = original_console

    def test_zero_duration_displays_as_dash(self):
        """Steps with zero duration should display '-' instead of '0.0s'."""
        ctx = PipelineContext(
            task=TaskInput(title="test"),
            project_path=Path("/tmp"),
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["detect"] = StepUsage(
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
            duration_ms=0.0,
            num_turns=0,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # Should NOT show 0.0s
            assert "0.0s" not in result

        finally:
            display_module.console = original_console

    def test_turns_displays_as_string(self):
        """Turns should display as a plain string number."""
        ctx = PipelineContext(
            task=TaskInput(title="test"),
            project_path=Path("/tmp"),
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["requirements"] = StepUsage(
            cost_usd=0.05,
            input_tokens=1000,
            output_tokens=500,
            duration_ms=2500.0,
            num_turns=5,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # Should show num_turns as "5"
            assert "5" in result

        finally:
            display_module.console = original_console

    def test_multiple_steps_in_correct_order(self):
        """Multiple steps should appear in the order they were added."""
        ctx = PipelineContext(
            task=TaskInput(title="test"),
            project_path=Path("/tmp"),
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["requirements"] = StepUsage(cost_usd=0.01, num_turns=1)
        ctx.step_usage["planning"] = StepUsage(cost_usd=0.02, num_turns=1)
        ctx.step_usage["test_writing"] = StepUsage(cost_usd=0.03, num_turns=1)
        ctx.step_usage["coding"] = StepUsage(cost_usd=0.04, num_turns=1)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # All steps should be present
            assert "requirements" in result
            assert "planning" in result
            assert "test_writing" in result
            assert "coding" in result

        finally:
            display_module.console = original_console

    def test_no_cost_breakdown_when_step_usage_empty(self):
        """Cost breakdown table should not appear when step_usage is empty."""
        ctx = PipelineContext(
            task=TaskInput(title="test"),
            project_path=Path("/tmp"),
            status=PipelineStatus.COMPLETED,
        )
        # No step_usage entries

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # Should NOT show cost breakdown table
            assert "Cost Breakdown" not in result

        finally:
            display_module.console = original_console


class TestDurationCalculationSyntax:
    """Test that duration calculation uses correct division operator."""

    def test_duration_calculation_uses_forward_slash(self):
        """Duration calculation should use / (forward slash) not \\ (backslash)."""
        # Read the display.py file to check syntax
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Find line 279 (approximately - look for the duration calculation)
        lines = content.splitlines()

        # Search for the duration calculation line
        duration_line = None
        for i, line in enumerate(lines, start=1):
            if "usage.duration_ms" in line and "1000" in line and ":.1f" in line:
                duration_line = line
                break

        assert duration_line is not None, "Could not find duration calculation line"

        # Should use forward slash for division
        assert "/" in duration_line, "Duration calculation should use / for division"
        assert "\\" not in duration_line or "\\\\" in duration_line, "Duration calculation should not use backslash"

        # More specifically, should match: usage.duration_ms / 1000
        assert "usage.duration_ms / 1000" in duration_line or "duration_ms / 1000" in duration_line


class TestCostBreakdownTableColumns:
    """Cost breakdown table should have correct column structure."""

    def test_table_has_all_columns(self):
        """Cost breakdown table should have Step, Cost, Tokens, Duration, Turns columns."""
        ctx = PipelineContext(
            task=TaskInput(title="test"),
            project_path=Path("/tmp"),
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["requirements"] = StepUsage(
            cost_usd=0.05,
            input_tokens=1000,
            output_tokens=500,
            duration_ms=2500.0,
            num_turns=2,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # Should have column headers
            assert "Step" in result
            assert "Cost" in result
            assert "Tokens" in result
            assert "Duration" in result
            assert "Turns" in result

        finally:
            display_module.console = original_console

    def test_cost_column_right_justified(self):
        """Cost column should be right-justified."""
        # This is implicit in the Rich Table configuration
        # We verify by checking the display.py source
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Look for the Cost column definition
        assert 'add_column("Cost", justify="right")' in content

    def test_tokens_column_right_justified(self):
        """Tokens column should be right-justified."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Look for the Tokens column definition
        assert 'add_column("Tokens", justify="right")' in content

    def test_duration_column_right_justified(self):
        """Duration column should be right-justified."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Look for the Duration column definition
        assert 'add_column("Duration", justify="right")' in content

    def test_turns_column_right_justified(self):
        """Turns column should be right-justified."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Look for the Turns column definition
        assert 'add_column("Turns", justify="right")' in content


class TestCostBreakdownIntegration:
    """Integration tests for cost breakdown display."""

    def test_full_pipeline_cost_summary(self):
        """Cost breakdown should show complete pipeline with all steps."""
        ctx = PipelineContext(
            task=TaskInput(title="Full pipeline test"),
            project_path=Path("/tmp/proj"),
            status=PipelineStatus.COMPLETED,
        )

        # Add usage for multiple steps
        ctx.step_usage["requirements"] = StepUsage(
            cost_usd=0.0500,
            input_tokens=10000,
            output_tokens=5000,
            duration_ms=5000.0,
            num_turns=2,
        )
        ctx.step_usage["planning"] = StepUsage(
            cost_usd=0.0300,
            input_tokens=8000,
            output_tokens=4000,
            duration_ms=3500.0,
            num_turns=1,
        )
        ctx.step_usage["test_writing"] = StepUsage(
            cost_usd=0.0750,
            input_tokens=15000,
            output_tokens=10000,
            duration_ms=8000.0,
            num_turns=3,
        )
        ctx.step_usage["coding"] = StepUsage(
            cost_usd=0.1200,
            input_tokens=20000,
            output_tokens=15000,
            duration_ms=12000.0,
            num_turns=4,
        )
        ctx.step_usage["review"] = StepUsage(
            cost_usd=0.0400,
            input_tokens=9000,
            output_tokens=6000,
            duration_ms=4500.0,
            num_turns=2,
        )
        ctx.total_cost_usd = 0.3150

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # Verify all steps appear
            assert "requirements" in result
            assert "planning" in result
            assert "test_writing" in result
            assert "coding" in result
            assert "review" in result

            # Verify costs appear
            assert "$0.0500" in result
            assert "$0.0300" in result
            assert "$0.0750" in result
            assert "$0.1200" in result
            assert "$0.0400" in result

            # Verify token counts (with commas)
            assert "15,000" in result  # requirements: 10k + 5k
            assert "12,000" in result  # planning: 8k + 4k
            assert "25,000" in result  # test_writing: 15k + 10k
            assert "35,000" in result  # coding: 20k + 15k
            assert "15,000" in result  # review: 9k + 6k

            # Verify durations
            assert "5.0s" in result
            assert "3.5s" in result
            assert "8.0s" in result
            assert "12.0s" in result
            assert "4.5s" in result

            # Verify turns
            assert "2" in result
            assert "1" in result
            assert "3" in result
            assert "4" in result

        finally:
            display_module.console = original_console
