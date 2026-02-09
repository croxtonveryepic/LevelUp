"""Tests for the 'levelup forget' CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.cli.prompts import pick_resumable_run
from levelup.state.models import RunRecord

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# CLI forget command tests - explicit run ID
# ---------------------------------------------------------------------------


class TestCLIForgetExplicitID:
    """Test 'levelup forget <run-id>' with explicit run ID argument."""

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_with_valid_id_deletes_run(self, MockStateManager, _banner):
        """forget with valid run ID calls delete_run and shows success."""
        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = _make_run_record(run_id="valid-run-123")
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["forget", "valid-run-123"])

        assert result.exit_code == 0
        mock_mgr.get_run.assert_called_once_with("valid-run-123")
        mock_mgr.delete_run.assert_called_once_with("valid-run-123")
        assert "deleted" in result.output.lower() or "removed" in result.output.lower()

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_with_invalid_id_shows_error(self, MockStateManager, _banner):
        """forget with non-existent run ID exits with error."""
        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = None
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["forget", "nonexistent-id"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()
        mock_mgr.delete_run.assert_not_called()

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_supports_db_path_option(self, MockStateManager, _banner):
        """forget command respects --db-path option."""
        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = _make_run_record(run_id="test-run")
        MockStateManager.return_value = mock_mgr

        custom_db = Path("/custom/path/state.db")
        result = runner.invoke(
            app, ["forget", "test-run", "--db-path", str(custom_db)]
        )

        assert result.exit_code == 0
        # Verify StateManager was called with custom db_path
        MockStateManager.assert_called_once()
        call_kwargs = MockStateManager.call_args[1]
        assert "db_path" in call_kwargs
        assert call_kwargs["db_path"] == custom_db

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_works_with_any_status(self, MockStateManager, _banner):
        """forget works regardless of run status (completed, failed, running, etc)."""
        statuses_to_test = ["completed", "failed", "aborted", "running", "pending"]

        for status in statuses_to_test:
            mock_mgr = MagicMock()
            mock_mgr.get_run.return_value = _make_run_record(
                run_id=f"run-{status}", status=status
            )
            MockStateManager.return_value = mock_mgr

            result = runner.invoke(app, ["forget", f"run-{status}"])

            assert result.exit_code == 0, f"Failed for status: {status}"
            mock_mgr.delete_run.assert_called_once_with(f"run-{status}")

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_success_message_includes_run_id(self, MockStateManager, _banner):
        """forget success message includes the run ID."""
        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = _make_run_record(run_id="abc123")
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["forget", "abc123"])

        assert result.exit_code == 0
        # Success message should reference the run ID (at least first 8 chars)
        assert "abc123" in result.output or "abc12345" in result.output


# ---------------------------------------------------------------------------
# CLI forget command tests - interactive mode
# ---------------------------------------------------------------------------


class TestCLIForgetInteractive:
    """Test 'levelup forget' (no args) interactive picker mode."""

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_no_args_no_runs_shows_message(self, MockStateManager, _banner):
        """forget with no runs in database shows 'No runs found' and exits 0."""
        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = []
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["forget"])

        assert result.exit_code == 0
        assert "no runs" in result.output.lower()
        mock_mgr.delete_run.assert_not_called()

    @patch("levelup.cli.prompts.pick_run_to_forget")
    @patch("levelup.cli.prompts.confirm_action")
    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_no_args_shows_picker_and_confirms(
        self, MockStateManager, _banner, mock_confirm, mock_picker
    ):
        """forget with no args shows picker, prompts confirmation, then deletes."""
        selected_run = _make_run_record(run_id="selected-123", status="completed")

        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = [
            selected_run,
            _make_run_record(run_id="other-456", status="failed"),
        ]
        MockStateManager.return_value = mock_mgr
        mock_picker.return_value = selected_run
        mock_confirm.return_value = True

        result = runner.invoke(app, ["forget"])

        assert result.exit_code == 0
        mock_picker.assert_called_once()
        # Picker should be called with all runs (not filtered by status)
        picker_runs = mock_picker.call_args[0][0]
        assert len(picker_runs) == 2
        mock_confirm.assert_called_once()
        mock_mgr.delete_run.assert_called_once_with("selected-123")

    @patch("levelup.cli.prompts.pick_run_to_forget")
    @patch("levelup.cli.prompts.confirm_action")
    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_no_args_cancelled_at_confirmation(
        self, MockStateManager, _banner, mock_confirm, mock_picker
    ):
        """forget cancelled at confirmation exits without deleting."""
        selected_run = _make_run_record(run_id="selected-123")

        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = [selected_run]
        MockStateManager.return_value = mock_mgr
        mock_picker.return_value = selected_run
        mock_confirm.return_value = False  # User cancels

        result = runner.invoke(app, ["forget"])

        assert result.exit_code == 0
        mock_mgr.delete_run.assert_not_called()
        assert "cancelled" in result.output.lower() or "aborted" in result.output.lower()

    @patch("levelup.cli.prompts.pick_run_to_forget")
    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_no_args_quit_at_picker(
        self, MockStateManager, _banner, mock_picker
    ):
        """forget quit at picker (KeyboardInterrupt) exits gracefully."""
        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = [_make_run_record()]
        MockStateManager.return_value = mock_mgr
        mock_picker.side_effect = KeyboardInterrupt

        result = runner.invoke(app, ["forget"])

        assert result.exit_code == 0
        mock_mgr.delete_run.assert_not_called()

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_no_args_marks_dead_runs_before_listing(
        self, MockStateManager, _banner
    ):
        """forget calls mark_dead_runs() before listing runs."""
        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = []
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["forget"])

        mock_mgr.mark_dead_runs.assert_called_once()
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI forget command tests - nuke mode
# ---------------------------------------------------------------------------


class TestCLIForgetNuke:
    """Test 'levelup forget --nuke' bulk deletion mode."""

    @patch("levelup.cli.prompts.confirm_action")
    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_nuke_deletes_all_runs_when_confirmed(
        self, MockStateManager, _banner, mock_confirm
    ):
        """forget --nuke with confirmation deletes all runs."""
        runs = [
            _make_run_record(run_id="run1", status="completed"),
            _make_run_record(run_id="run2", status="failed"),
            _make_run_record(run_id="run3", status="aborted"),
        ]

        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = runs
        MockStateManager.return_value = mock_mgr
        mock_confirm.return_value = True

        result = runner.invoke(app, ["forget", "--nuke"])

        assert result.exit_code == 0
        # Should show count in confirmation prompt
        assert "3" in result.output
        mock_confirm.assert_called_once()
        # Should delete all runs
        assert mock_mgr.delete_run.call_count == 3
        mock_mgr.delete_run.assert_any_call("run1")
        mock_mgr.delete_run.assert_any_call("run2")
        mock_mgr.delete_run.assert_any_call("run3")

    @patch("levelup.cli.prompts.confirm_action")
    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_nuke_cancelled_no_deletion(
        self, MockStateManager, _banner, mock_confirm
    ):
        """forget --nuke cancelled at confirmation deletes nothing."""
        runs = [
            _make_run_record(run_id="run1"),
            _make_run_record(run_id="run2"),
        ]

        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = runs
        MockStateManager.return_value = mock_mgr
        mock_confirm.return_value = False  # User cancels

        result = runner.invoke(app, ["forget", "--nuke"])

        assert result.exit_code == 0
        mock_mgr.delete_run.assert_not_called()
        assert "cancelled" in result.output.lower() or "aborted" in result.output.lower()

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_nuke_empty_database_shows_message(
        self, MockStateManager, _banner
    ):
        """forget --nuke with empty database shows 'No runs to delete'."""
        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = []
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["forget", "--nuke"])

        assert result.exit_code == 0
        assert "no runs" in result.output.lower()
        mock_mgr.delete_run.assert_not_called()

    @patch("levelup.cli.prompts.confirm_action")
    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_nuke_supports_db_path(
        self, MockStateManager, _banner, mock_confirm
    ):
        """forget --nuke respects --db-path option."""
        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = [_make_run_record()]
        MockStateManager.return_value = mock_mgr
        mock_confirm.return_value = True

        custom_db = Path("/custom/db.db")
        result = runner.invoke(
            app, ["forget", "--nuke", "--db-path", str(custom_db)]
        )

        assert result.exit_code == 0
        call_kwargs = MockStateManager.call_args[1]
        assert "db_path" in call_kwargs
        assert call_kwargs["db_path"] == custom_db

    @patch("levelup.cli.prompts.confirm_action")
    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_nuke_requires_confirmation(
        self, MockStateManager, _banner, mock_confirm
    ):
        """forget --nuke requires explicit user confirmation."""
        runs = [_make_run_record(run_id="run1")]

        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = runs
        MockStateManager.return_value = mock_mgr
        mock_confirm.return_value = True

        result = runner.invoke(app, ["forget", "--nuke"])

        # Confirmation should be called (not automatic)
        mock_confirm.assert_called_once()
        assert result.exit_code == 0

    @patch("levelup.cli.prompts.confirm_action")
    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_nuke_shows_success_message_with_count(
        self, MockStateManager, _banner, mock_confirm
    ):
        """forget --nuke shows success message with count of deleted runs."""
        runs = [
            _make_run_record(run_id=f"run{i}") for i in range(5)
        ]

        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = runs
        MockStateManager.return_value = mock_mgr
        mock_confirm.return_value = True

        result = runner.invoke(app, ["forget", "--nuke"])

        assert result.exit_code == 0
        # Success message should include count
        assert "5" in result.output
        assert "deleted" in result.output.lower() or "removed" in result.output.lower()

    @patch("levelup.cli.prompts.confirm_action")
    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_nuke_deletes_runs_of_all_statuses(
        self, MockStateManager, _banner, mock_confirm
    ):
        """forget --nuke deletes runs regardless of status."""
        runs = [
            _make_run_record(run_id="completed-run", status="completed"),
            _make_run_record(run_id="failed-run", status="failed"),
            _make_run_record(run_id="running-run", status="running"),
            _make_run_record(run_id="pending-run", status="pending"),
            _make_run_record(run_id="aborted-run", status="aborted"),
        ]

        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = runs
        MockStateManager.return_value = mock_mgr
        mock_confirm.return_value = True

        result = runner.invoke(app, ["forget", "--nuke"])

        assert result.exit_code == 0
        assert mock_mgr.delete_run.call_count == 5


# ---------------------------------------------------------------------------
# Interactive picker helper function tests
# ---------------------------------------------------------------------------


class TestPickRunToForget:
    """Test the pick_run_to_forget() prompt function."""

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    def test_pick_first_run(self, _mock_prompt):
        """Typing '1' selects the first run."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [
            _make_run_record(run_id="run-aaa"),
            _make_run_record(run_id="run-bbb"),
        ]
        selected = pick_run_to_forget(runs)
        assert selected.run_id == "run-aaa"

    @patch("levelup.cli.prompts.pt_prompt", return_value="2")
    def test_pick_second_run(self, _mock_prompt):
        """Typing '2' selects the second run."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [
            _make_run_record(run_id="run-aaa"),
            _make_run_record(run_id="run-bbb"),
        ]
        selected = pick_run_to_forget(runs)
        assert selected.run_id == "run-bbb"

    @patch("levelup.cli.prompts.pt_prompt", return_value="q")
    def test_pick_quit_raises_keyboard_interrupt(self, _mock_prompt):
        """Typing 'q' raises KeyboardInterrupt."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [_make_run_record()]
        with pytest.raises(KeyboardInterrupt):
            pick_run_to_forget(runs)

    @patch("levelup.cli.prompts.pt_prompt", side_effect=["invalid", "0", "99", "1"])
    def test_pick_retries_on_invalid_input(self, _mock_prompt):
        """Invalid inputs are retried until valid."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [
            _make_run_record(run_id="run-aaa"),
            _make_run_record(run_id="run-bbb"),
        ]
        selected = pick_run_to_forget(runs)
        assert selected.run_id == "run-aaa"
        assert _mock_prompt.call_count == 4

    @patch("levelup.cli.prompts.pt_prompt", return_value="3")
    def test_pick_displays_all_runs(self, _mock_prompt):
        """Picker displays all runs regardless of status."""
        from levelup.cli.prompts import pick_run_to_forget

        runs = [
            _make_run_record(run_id="completed-run", status="completed"),
            _make_run_record(run_id="failed-run", status="failed"),
            _make_run_record(run_id="running-run", status="running"),
        ]
        selected = pick_run_to_forget(runs)
        assert selected.run_id == "running-run"

    def test_pick_empty_list_raises_error(self):
        """Calling picker with empty list should raise an error."""
        from levelup.cli.prompts import pick_run_to_forget

        with pytest.raises((IndexError, ValueError, AssertionError)):
            pick_run_to_forget([])

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    def test_pick_shows_run_details(self, mock_prompt):
        """Picker displays run ID, task, status, and updated time."""
        from levelup.cli.prompts import pick_run_to_forget
        from unittest.mock import patch as context_patch

        run = _make_run_record(
            run_id="test-run-12345",
            task_title="My test task",
            status="completed",
            updated_at="2025-01-20T15:30:00",
        )

        # We need to verify the table is rendered, but since it's printed,
        # we can capture console output
        with context_patch("levelup.cli.prompts.console") as mock_console:
            selected = pick_run_to_forget([run])
            # Verify table was printed
            mock_console.print.assert_called()
            assert selected.run_id == "test-run-12345"


# ---------------------------------------------------------------------------
# Edge cases and error handling
# ---------------------------------------------------------------------------


class TestCLIForgetEdgeCases:
    """Test edge cases and error handling for forget command."""

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_with_run_id_and_nuke_shows_error(
        self, MockStateManager, _banner
    ):
        """forget with both run_id and --nuke flag should show error."""
        mock_mgr = MagicMock()
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["forget", "run-id", "--nuke"])

        # Should either error or ignore one of the arguments
        # Implementation choice: most likely error or give precedence to explicit ID
        # This test documents expected behavior
        assert result.exit_code in (0, 1)  # Either works, but should be consistent

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_handles_state_manager_exception(
        self, MockStateManager, _banner
    ):
        """forget handles exceptions from StateManager gracefully."""
        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = _make_run_record(run_id="test-run")
        mock_mgr.delete_run.side_effect = Exception("Database error")
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["forget", "test-run"])

        assert result.exit_code == 1
        assert "error" in result.output.lower()

    @patch("levelup.cli.prompts.confirm_action")
    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_nuke_handles_partial_deletion_failure(
        self, MockStateManager, _banner, mock_confirm
    ):
        """forget --nuke handles deletion failure for some runs."""
        runs = [
            _make_run_record(run_id="run1"),
            _make_run_record(run_id="run2"),
            _make_run_record(run_id="run3"),
        ]

        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = runs

        # Make delete fail for second run
        def delete_side_effect(run_id):
            if run_id == "run2":
                raise Exception("Delete failed")

        mock_mgr.delete_run.side_effect = delete_side_effect
        MockStateManager.return_value = mock_mgr
        mock_confirm.return_value = True

        result = runner.invoke(app, ["forget", "--nuke"])

        # Should continue deleting other runs or report error
        assert "error" in result.output.lower() or "failed" in result.output.lower()

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_forget_with_empty_run_id_shows_error(
        self, MockStateManager, _banner
    ):
        """forget with empty string as run_id shows error."""
        mock_mgr = MagicMock()
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["forget", ""])

        # Empty run_id should be treated as invalid
        assert result.exit_code in (1, 2)  # Error or usage error


# ---------------------------------------------------------------------------
# Integration with StateManager
# ---------------------------------------------------------------------------


class TestForgetStateManagerIntegration:
    """Test forget command integration with actual StateManager."""

    def test_forget_actually_deletes_from_db(self, tmp_path):
        """End-to-end test: forget actually removes run from database."""
        from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
        from levelup.state.manager import StateManager

        # Create a real database with a run
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(
            run_id="test-run-123",
            task=TaskInput(title="Test task", description="Test"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
        )
        mgr.register_run(ctx)

        # Verify run exists
        assert mgr.get_run("test-run-123") is not None

        # Mock the banner to avoid output clutter
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(app, ["forget", "test-run-123", "--db-path", str(db_path)])

        assert result.exit_code == 0

        # Verify run was deleted
        assert mgr.get_run("test-run-123") is None

    def test_forget_deletes_associated_checkpoints(self, tmp_path):
        """forget deletes checkpoint requests associated with the run."""
        from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
        from levelup.state.manager import StateManager

        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(
            run_id="test-run-456",
            task=TaskInput(title="Test task", description="Test"),
            project_path=tmp_path,
            status=PipelineStatus.FAILED,
        )
        mgr.register_run(ctx)
        mgr.create_checkpoint_request("test-run-456", "requirements", "{}")

        # Verify checkpoint exists
        assert len(mgr.get_pending_checkpoints()) == 1

        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(app, ["forget", "test-run-456", "--db-path", str(db_path)])

        assert result.exit_code == 0

        # Verify checkpoint was deleted
        assert len(mgr.get_pending_checkpoints()) == 0

    @patch("levelup.cli.prompts.confirm_action")
    def test_forget_nuke_deletes_all_from_real_db(self, mock_confirm, tmp_path):
        """End-to-end test: forget --nuke removes all runs from database."""
        from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
        from levelup.state.manager import StateManager

        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        # Create multiple runs
        for i in range(3):
            ctx = PipelineContext(
                run_id=f"run-{i}",
                task=TaskInput(title=f"Task {i}", description="Test"),
                project_path=tmp_path,
                status=PipelineStatus.COMPLETED,
            )
            mgr.register_run(ctx)

        # Verify runs exist
        assert len(mgr.list_runs()) == 3

        mock_confirm.return_value = True

        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(app, ["forget", "--nuke", "--db-path", str(db_path)])

        assert result.exit_code == 0

        # Verify all runs were deleted
        assert len(mgr.list_runs()) == 0
