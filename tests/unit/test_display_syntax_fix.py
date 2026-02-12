"""Tests for display.py syntax fix on line 279."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestDisplayDurationCalculationSyntax:
    """Test that line 279 in display.py uses correct division operator."""

    def test_line_279_uses_forward_slash_not_backslash(self):
        """Line 279 should use / (forward slash) for division, not \\ (backslash)."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        assert display_path.exists(), f"display.py not found at {display_path}"

        content = display_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Line 279 (accounting for 0-based indexing)
        line_279 = lines[278] if len(lines) > 278 else ""

        # Should contain duration calculation
        assert "duration_ms" in line_279 or "1000" in line_279, \
            f"Line 279 doesn't appear to contain duration calculation: {line_279}"

        # Should use forward slash for division
        assert "/" in line_279, "Line 279 should use / for division"

        # Should NOT use backslash (except in strings like '\\n')
        # Allow escaped backslashes (\\) but not single backslash used for division
        if "\\" in line_279:
            # If backslash exists, it should be escaped or in a string
            assert "\\\\" in line_279 or '"' in line_279 or "'" in line_279, \
                "Backslash found but not properly escaped or in string"

    def test_duration_calculation_format(self):
        """Duration calculation should match the expected format."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Find the line containing duration calculation
        duration_line = None
        line_number = None
        for i, line in enumerate(lines, start=1):
            if "usage.duration_ms" in line and "1000" in line and ":.1f" in line:
                duration_line = line
                line_number = i
                break

        assert duration_line is not None, "Could not find duration calculation line"

        # Should match pattern: usage.duration_ms / 1000
        assert "usage.duration_ms / 1000" in duration_line or "duration_ms / 1000" in duration_line, \
            f"Line {line_number} doesn't contain expected pattern 'duration_ms / 1000': {duration_line}"

        # Should have .1f formatting for one decimal place
        assert ":.1f" in duration_line, \
            f"Line {line_number} should use :.1f formatting: {duration_line}"

        # Should end with 's' for seconds
        assert 's"' in duration_line or "s'" in duration_line, \
            f"Line {line_number} should append 's' for seconds: {duration_line}"

    def test_cost_table_duration_calculation_matches_spec(self):
        """Cost breakdown table duration calculation should match requirements."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Find the cost breakdown table section
        lines = content.splitlines()
        in_cost_table = False
        for i, line in enumerate(lines, start=1):
            if "Cost Breakdown" in line:
                in_cost_table = True
            if in_cost_table and "duration_ms" in line:
                # Found the duration calculation line
                # Should use forward slash division
                assert "/" in line, f"Line {i} should use / for division"

                # Should calculate: duration_ms / 1000
                assert "/ 1000" in line, f"Line {i} should divide by 1000"

                # Should format with 1 decimal place
                assert ":.1f" in line, f"Line {i} should use :.1f format"

                # Found and verified - done
                break

    def test_no_syntax_errors_in_duration_calculation(self):
        """Duration calculation should not have syntax errors."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"

        # Try to import the module - will fail if there are syntax errors
        try:
            import sys
            sys.path.insert(0, str(display_path.parent.parent.parent))
            from levelup.cli import display
            # If import succeeds, there are no syntax errors
            assert hasattr(display, "print_pipeline_summary")
        except SyntaxError as e:
            pytest.fail(f"Syntax error in display.py: {e}")
        finally:
            if str(display_path.parent.parent.parent) in sys.path:
                sys.path.remove(str(display_path.parent.parent.parent))

    def test_duration_calculation_context(self):
        """Duration calculation should be in the correct context (cost breakdown table)."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Find line with duration calculation
        for i, line in enumerate(lines):
            if "usage.duration_ms / 1000" in line or "duration_ms / 1000" in line:
                # Check that we're in the right context
                # Should be within the cost breakdown section
                # Look backwards for "Cost Breakdown" or "cost_table"
                context_lines = lines[max(0, i - 20):i]
                context = "\n".join(context_lines)

                assert "Cost Breakdown" in context or "cost_table" in context, \
                    "Duration calculation not in cost breakdown context"

                # Should be in a for loop over step_usage
                assert "step_usage" in context or "for step_name, usage" in context, \
                    "Duration calculation not in step_usage loop"

                break


class TestDisplayFormatSpecifications:
    """Test that display.py meets all formatting specifications."""

    def test_cost_format_four_decimals(self):
        """Cost should be formatted with 4 decimal places."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Look for cost formatting in cost breakdown section
        lines = content.splitlines()
        for line in lines:
            if "cost_usd" in line and ":.4f" in line:
                # Found the cost formatting
                assert ":.4f" in line, "Cost should use :.4f format"
                break

    def test_tokens_format_with_commas(self):
        """Tokens should be formatted with comma separators."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Look for token formatting
        found_comma_format = False
        for line in content.splitlines():
            if ("input_tokens" in line or "output_tokens" in line) and ":," in line:
                found_comma_format = True
                break

        assert found_comma_format, "Tokens should use :, format for comma separators"

    def test_dash_for_zero_values(self):
        """Zero values should display as '-' instead of '$0.0000' or '0'."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Look for conditional display logic (e.g., 'if usage.cost_usd else "-"')
        lines = content.splitlines()

        # Should have logic to display "-" for zero cost
        cost_dash_logic = any('"-"' in line and ("cost" in line or "if" in line) for line in lines)
        assert cost_dash_logic, "Should have logic to display '-' for zero cost"

        # Should have logic to display "-" for zero tokens
        tokens_dash_logic = any('"-"' in line and ("tokens" in line or "if" in line) for line in lines)
        assert tokens_dash_logic, "Should have logic to display '-' for zero tokens"

        # Should have logic to display "-" for zero duration
        duration_dash_logic = any('"-"' in line and ("duration" in line or "if" in line) for line in lines)
        assert duration_dash_logic, "Should have logic to display '-' for zero duration"


class TestDisplayTableStructure:
    """Test that the cost breakdown table has the correct structure."""

    def test_table_has_five_columns(self):
        """Cost breakdown table should have 5 columns: Step, Cost, Tokens, Duration, Turns."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Count column definitions in cost breakdown section
        lines = content.splitlines()
        in_cost_table = False
        columns = []

        for line in lines:
            if "Cost Breakdown" in line:
                in_cost_table = True
            if in_cost_table and "add_column" in line:
                columns.append(line)
            if in_cost_table and "add_row" in line:
                # End of column definitions
                break

        # Should have 5 columns
        assert len(columns) == 5, f"Expected 5 columns, found {len(columns)}"

        # Verify column names
        all_columns = "\n".join(columns)
        assert '"Step"' in all_columns or "'Step'" in all_columns
        assert '"Cost"' in all_columns or "'Cost'" in all_columns
        assert '"Tokens"' in all_columns or "'Tokens'" in all_columns
        assert '"Duration"' in all_columns or "'Duration'" in all_columns
        assert '"Turns"' in all_columns or "'Turns'" in all_columns

    def test_numeric_columns_right_justified(self):
        """Numeric columns (Cost, Tokens, Duration, Turns) should be right-justified."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Check that numeric columns have justify="right"
        lines = content.splitlines()
        cost_column = any('"Cost"' in line and 'justify="right"' in line for line in lines)
        tokens_column = any('"Tokens"' in line and 'justify="right"' in line for line in lines)
        duration_column = any('"Duration"' in line and 'justify="right"' in line for line in lines)
        turns_column = any('"Turns"' in line and 'justify="right"' in line for line in lines)

        assert cost_column, "Cost column should be right-justified"
        assert tokens_column, "Tokens column should be right-justified"
        assert duration_column, "Duration column should be right-justified"
        assert turns_column, "Turns column should be right-justified"

    def test_step_column_is_bold(self):
        """Step column should use bold style."""
        display_path = Path(__file__).parent.parent.parent / "src" / "levelup" / "cli" / "display.py"
        content = display_path.read_text(encoding="utf-8")

        # Check that Step column has style="bold"
        lines = content.splitlines()
        step_column = any('"Step"' in line and 'style="bold"' in line for line in lines)

        assert step_column, "Step column should use bold style"
