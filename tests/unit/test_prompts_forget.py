"""Tests for pick_run_to_forget() helper function in prompts.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from levelup.state.models import RunRecord


def _make_run_record(**overrides) -> RunRecord:
    """Build a RunRecord with sensible defaults."""
    defaults = dict(
        run_id="abc12345-6789-0000-0000-000000000000",
        task_title="Test task",
        project_path="/tmp/test",
        status="failed",
        current_step="coding",
        context_json='{"some": "json"}',
        started_at="2025-01-15T10:00:00",
        updated_at="2025-01-15T12:00:00",
    )
    defaults.update(overrides)
    return RunRecord(**defaults)


class TestPickRunToForget:
    """Test the pick_run_to_forget() interactive prompt helper."""

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    def test_select_first_run_by_number(self, _mock_prompt):
        """User inputs '1' to select the first run."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [
            _make_run_record(run_id="run-111", task_title="First task"),
            _make_run_record(run_id="run-222", task_title="Second task"),
            _make_run_record(run_id="run-333", task_title="Third task"),
        ]

        selected = pick_run_to_forget(runs)

        assert selected.run_id == "run-111"
        assert selected.task_title == "First task"

    @patch("levelup.cli.prompts.pt_prompt", return_value="3")
    def test_select_third_run_by_number(self, _mock_prompt):
        """User inputs '3' to select the third run."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [
            _make_run_record(run_id="run-111"),
            _make_run_record(run_id="run-222"),
            _make_run_record(run_id="run-333"),
        ]

        selected = pick_run_to_forget(runs)

        assert selected.run_id == "run-333"

    @patch("levelup.cli.prompts.pt_prompt", return_value="q")
    def test_quit_with_q_raises_keyboard_interrupt(self, _mock_prompt):
        """User inputs 'q' to quit, raising KeyboardInterrupt."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [_make_run_record()]

        with pytest.raises(KeyboardInterrupt):
            pick_run_to_forget(runs)

    @patch("levelup.cli.prompts.pt_prompt", return_value="quit")
    def test_quit_with_quit_raises_keyboard_interrupt(self, _mock_prompt):
        """User inputs 'quit' to quit, raising KeyboardInterrupt."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [_make_run_record()]

        with pytest.raises(KeyboardInterrupt):
            pick_run_to_forget(runs)

    @patch("levelup.cli.prompts.pt_prompt", side_effect=["invalid", "1"])
    def test_invalid_input_prompts_retry(self, _mock_prompt):
        """Invalid non-numeric input causes re-prompt."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [_make_run_record(run_id="run-111")]

        selected = pick_run_to_forget(runs)

        assert selected.run_id == "run-111"
        assert _mock_prompt.call_count == 2

    @patch("levelup.cli.prompts.pt_prompt", side_effect=["0", "1"])
    def test_zero_input_prompts_retry(self, _mock_prompt):
        """Input '0' (out of range) causes re-prompt."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [_make_run_record(run_id="run-111")]

        selected = pick_run_to_forget(runs)

        assert selected.run_id == "run-111"
        assert _mock_prompt.call_count == 2

    @patch("levelup.cli.prompts.pt_prompt", side_effect=["99", "1"])
    def test_out_of_range_input_prompts_retry(self, _mock_prompt):
        """Input beyond list length causes re-prompt."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [
            _make_run_record(run_id="run-111"),
            _make_run_record(run_id="run-222"),
        ]

        selected = pick_run_to_forget(runs)

        assert selected.run_id == "run-111"
        assert _mock_prompt.call_count == 2

    @patch("levelup.cli.prompts.pt_prompt", side_effect=["", "-1", "abc", "2"])
    def test_multiple_invalid_inputs_retry_until_valid(self, _mock_prompt):
        """Multiple invalid inputs are retried until valid."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [
            _make_run_record(run_id="run-111"),
            _make_run_record(run_id="run-222"),
        ]

        selected = pick_run_to_forget(runs)

        assert selected.run_id == "run-222"
        assert _mock_prompt.call_count == 4

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    @patch("levelup.cli.prompts.console")
    def test_displays_table_with_run_details(self, mock_console, _mock_prompt):
        """Displays Rich table with run ID, task, status, step, and updated time."""
        from levelup.cli.prompts import pick_run_to_forget

        run = _make_run_record(
            run_id="test-run-12345678",
            task_title="My test task",
            status="completed",
            current_step="review",
            updated_at="2025-01-20T15:30:45",
        )

        selected = pick_run_to_forget([run])

        # Verify table was printed
        assert mock_console.print.called
        # Verify selected run
        assert selected.run_id == "test-run-12345678"

    @patch("levelup.cli.prompts.pt_prompt", return_value="2")
    def test_handles_runs_with_all_statuses(self, _mock_prompt):
        """Picker works with runs of any status."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [
            _make_run_record(run_id="completed-run", status="completed"),
            _make_run_record(run_id="failed-run", status="failed"),
            _make_run_record(run_id="running-run", status="running"),
            _make_run_record(run_id="aborted-run", status="aborted"),
            _make_run_record(run_id="pending-run", status="pending"),
        ]

        selected = pick_run_to_forget(runs)

        assert selected.run_id == "failed-run"

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    def test_handles_run_without_context_json(self, _mock_prompt):
        """Picker handles runs that don't have context_json."""
        from levelup.cli.prompts import pick_run_to_forget

        run = _make_run_record(run_id="no-context-run", context_json=None)

        selected = pick_run_to_forget([run])

        assert selected.run_id == "no-context-run"

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    def test_handles_run_without_current_step(self, _mock_prompt):
        """Picker handles runs that don't have current_step."""
        from levelup.cli.prompts import pick_run_to_forget

        run = _make_run_record(run_id="no-step-run", current_step=None)

        selected = pick_run_to_forget([run])

        assert selected.run_id == "no-step-run"

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    def test_handles_run_with_empty_task_title(self, _mock_prompt):
        """Picker handles runs with empty/None task title."""
        from levelup.cli.prompts import pick_run_to_forget

        run = _make_run_record(run_id="no-title-run", task_title=None)

        selected = pick_run_to_forget([run])

        assert selected.run_id == "no-title-run"

    def test_empty_runs_list_raises_error(self):
        """Calling picker with empty list raises appropriate error."""
        from levelup.cli.prompts import pick_run_to_forget

        # Empty list should raise an error (can't pick from nothing)
        with pytest.raises((IndexError, ValueError, AssertionError)):
            pick_run_to_forget([])

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    def test_single_run_selectable(self, _mock_prompt):
        """Picker works correctly with a single run."""
        from levelup.cli.prompts import pick_run_to_forget

        run = _make_run_record(run_id="only-run")

        selected = pick_run_to_forget([run])

        assert selected.run_id == "only-run"

    @patch("levelup.cli.prompts.pt_prompt", return_value="10")
    def test_large_list_of_runs(self, _mock_prompt):
        """Picker handles larger lists of runs correctly."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [_make_run_record(run_id=f"run-{i:03d}") for i in range(20)]

        selected = pick_run_to_forget(runs)

        assert selected.run_id == "run-009"  # 10th run (0-indexed 9)

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    @patch("levelup.cli.prompts.console")
    def test_table_shows_truncated_run_id(self, mock_console, _mock_prompt):
        """Table displays first 8-10 chars of run ID for readability."""
        from levelup.cli.prompts import pick_run_to_forget

        run = _make_run_record(
            run_id="very-long-run-id-12345678-1234-5678-1234-567812345678"
        )

        selected = pick_run_to_forget([run])

        # Table should be printed
        assert mock_console.print.called
        assert selected.run_id == "very-long-run-id-12345678-1234-5678-1234-567812345678"

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    @patch("levelup.cli.prompts.console")
    def test_table_formats_timestamp(self, mock_console, _mock_prompt):
        """Table formats ISO timestamp for display (removes 'T', shows date+time)."""
        from levelup.cli.prompts import pick_run_to_forget

        run = _make_run_record(updated_at="2025-01-20T15:30:45.123456")

        selected = pick_run_to_forget([run])

        assert mock_console.print.called
        assert selected.run_id == "abc12345-6789-0000-0000-000000000000"

    @patch("levelup.cli.prompts.pt_prompt", return_value="Q")
    def test_quit_case_insensitive(self, _mock_prompt):
        """'Q' (uppercase) also quits."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [_make_run_record()]

        with pytest.raises(KeyboardInterrupt):
            pick_run_to_forget(runs)

    @patch("levelup.cli.prompts.pt_prompt", return_value="  2  ")
    def test_whitespace_trimmed_from_input(self, _mock_prompt):
        """Leading/trailing whitespace is trimmed from input."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [
            _make_run_record(run_id="run-111"),
            _make_run_record(run_id="run-222"),
        ]

        selected = pick_run_to_forget(runs)

        assert selected.run_id == "run-222"

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    @patch("levelup.cli.prompts.console")
    def test_displays_instruction_message(self, mock_console, _mock_prompt):
        """Displays instruction to enter number or 'q' to quit."""
        from levelup.cli.prompts import pick_run_to_forget

        run = _make_run_record()

        pick_run_to_forget([run])

        # Should print instructions
        assert mock_console.print.called
        # Verify instructions were shown (check call args contain relevant text)
        call_args_list = [str(call) for call in mock_console.print.call_args_list]
        instructions_shown = any(
            "quit" in str(call).lower() or "number" in str(call).lower()
            for call in call_args_list
        )
        assert instructions_shown

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    def test_returns_run_record_object(self, _mock_prompt):
        """Function returns a RunRecord object."""
        from levelup.cli.prompts import pick_run_to_forget

        run = _make_run_record()
        selected = pick_run_to_forget([run])

        assert isinstance(selected, RunRecord)
        assert hasattr(selected, "run_id")
        assert hasattr(selected, "task_title")
        assert hasattr(selected, "status")
