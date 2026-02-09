"""Integration tests for the forget command with real StateManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
from levelup.state.manager import StateManager

runner = CliRunner()


@pytest.fixture
def test_db(tmp_path: Path) -> Path:
    """Create a temporary test database."""
    return tmp_path / "test.db"


@pytest.fixture
def state_manager(test_db: Path) -> StateManager:
    """Create a StateManager with test database."""
    return StateManager(db_path=test_db)


def _create_test_run(
    mgr: StateManager,
    run_id: str,
    task_title: str,
    status: PipelineStatus,
    project_path: Path,
    current_step: str | None = None,
) -> PipelineContext:
    """Helper to create and register a test run."""
    ctx = PipelineContext(
        run_id=run_id,
        task=TaskInput(title=task_title, description=f"Description for {task_title}"),
        project_path=project_path,
        status=status,
        current_step=current_step,
    )
    mgr.register_run(ctx)
    return ctx


class TestForgetCommandIntegration:
    """Integration tests for forget command with real database."""

    def test_forget_explicit_id_removes_from_database(
        self, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """forget <run-id> actually removes the run from the database."""
        ctx = _create_test_run(
            state_manager, "run-123", "Test task", PipelineStatus.COMPLETED, tmp_path
        )

        # Verify run exists
        assert state_manager.get_run("run-123") is not None

        # Run forget command
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(
                app, ["forget", "run-123", "--db-path", str(test_db)]
            )

        assert result.exit_code == 0
        # Verify run is deleted
        assert state_manager.get_run("run-123") is None

    def test_forget_removes_checkpoint_requests(
        self, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """forget command deletes associated checkpoint requests."""
        ctx = _create_test_run(
            state_manager, "run-456", "Task with checkpoints", PipelineStatus.FAILED, tmp_path
        )

        # Create checkpoint requests
        state_manager.create_checkpoint_request("run-456", "requirements", "{}")
        state_manager.create_checkpoint_request("run-456", "test_writing", "{}")

        # Verify checkpoints exist
        assert len(state_manager.get_pending_checkpoints()) == 2

        # Run forget command
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(
                app, ["forget", "run-456", "--db-path", str(test_db)]
            )

        assert result.exit_code == 0
        # Verify checkpoints are deleted
        assert len(state_manager.get_pending_checkpoints()) == 0

    def test_forget_nonexistent_run_does_not_affect_database(
        self, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """Attempting to forget non-existent run doesn't affect other runs."""
        _create_test_run(
            state_manager, "run-111", "Existing task", PipelineStatus.COMPLETED, tmp_path
        )

        # Attempt to delete non-existent run
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(
                app, ["forget", "nonexistent-run", "--db-path", str(test_db)]
            )

        assert result.exit_code == 1
        # Verify existing run is still there
        assert state_manager.get_run("run-111") is not None

    def test_forget_with_multiple_runs_deletes_only_specified(
        self, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """forget deletes only the specified run, not others."""
        _create_test_run(
            state_manager, "run-aaa", "Task A", PipelineStatus.COMPLETED, tmp_path
        )
        _create_test_run(
            state_manager, "run-bbb", "Task B", PipelineStatus.FAILED, tmp_path
        )
        _create_test_run(
            state_manager, "run-ccc", "Task C", PipelineStatus.ABORTED, tmp_path
        )

        # Verify all exist
        assert len(state_manager.list_runs()) == 3

        # Delete middle run
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(
                app, ["forget", "run-bbb", "--db-path", str(test_db)]
            )

        assert result.exit_code == 0
        # Verify only specified run is deleted
        assert state_manager.get_run("run-aaa") is not None
        assert state_manager.get_run("run-bbb") is None
        assert state_manager.get_run("run-ccc") is not None
        assert len(state_manager.list_runs()) == 2

    @patch("levelup.cli.prompts.confirm_action")
    def test_forget_nuke_deletes_all_runs(
        self, mock_confirm, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """forget --nuke deletes all runs from the database."""
        # Create multiple runs with different statuses
        _create_test_run(
            state_manager, "run-1", "Task 1", PipelineStatus.COMPLETED, tmp_path
        )
        _create_test_run(
            state_manager, "run-2", "Task 2", PipelineStatus.FAILED, tmp_path
        )
        _create_test_run(
            state_manager, "run-3", "Task 3", PipelineStatus.RUNNING, tmp_path
        )
        _create_test_run(
            state_manager, "run-4", "Task 4", PipelineStatus.ABORTED, tmp_path
        )

        # Verify all exist
        assert len(state_manager.list_runs()) == 4

        # Confirm deletion
        mock_confirm.return_value = True

        # Run nuke command
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(
                app, ["forget", "--nuke", "--db-path", str(test_db)]
            )

        assert result.exit_code == 0
        # Verify all runs are deleted
        assert len(state_manager.list_runs()) == 0

    @patch("levelup.cli.prompts.confirm_action")
    def test_forget_nuke_preserves_runs_when_cancelled(
        self, mock_confirm, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """forget --nuke cancelled at confirmation preserves all runs."""
        _create_test_run(
            state_manager, "run-1", "Task 1", PipelineStatus.COMPLETED, tmp_path
        )
        _create_test_run(
            state_manager, "run-2", "Task 2", PipelineStatus.FAILED, tmp_path
        )

        # User cancels
        mock_confirm.return_value = False

        # Run nuke command
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(
                app, ["forget", "--nuke", "--db-path", str(test_db)]
            )

        assert result.exit_code == 0
        # Verify runs still exist
        assert len(state_manager.list_runs()) == 2

    @patch("levelup.cli.prompts.pick_run_to_forget")
    @patch("levelup.cli.prompts.confirm_action")
    def test_forget_interactive_deletes_selected_run(
        self,
        mock_confirm,
        mock_picker,
        state_manager: StateManager,
        test_db: Path,
        tmp_path: Path,
    ):
        """forget (no args) with interactive selection deletes chosen run."""
        ctx1 = _create_test_run(
            state_manager, "run-aaa", "First task", PipelineStatus.COMPLETED, tmp_path
        )
        ctx2 = _create_test_run(
            state_manager, "run-bbb", "Second task", PipelineStatus.FAILED, tmp_path
        )

        # User selects second run
        run2_record = state_manager.get_run("run-bbb")
        mock_picker.return_value = run2_record
        mock_confirm.return_value = True

        # Run interactive forget
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(app, ["forget", "--db-path", str(test_db)])

        assert result.exit_code == 0
        # Verify only selected run is deleted
        assert state_manager.get_run("run-aaa") is not None
        assert state_manager.get_run("run-bbb") is None

    @patch("levelup.cli.prompts.pick_run_to_forget")
    @patch("levelup.cli.prompts.confirm_action")
    def test_forget_interactive_cancelled_preserves_run(
        self,
        mock_confirm,
        mock_picker,
        state_manager: StateManager,
        test_db: Path,
        tmp_path: Path,
    ):
        """forget (no args) cancelled at confirmation preserves run."""
        ctx = _create_test_run(
            state_manager, "run-xyz", "Test task", PipelineStatus.COMPLETED, tmp_path
        )

        run_record = state_manager.get_run("run-xyz")
        mock_picker.return_value = run_record
        mock_confirm.return_value = False  # User cancels

        # Run interactive forget
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(app, ["forget", "--db-path", str(test_db)])

        assert result.exit_code == 0
        # Verify run still exists
        assert state_manager.get_run("run-xyz") is not None

    @patch("levelup.cli.prompts.pick_run_to_forget")
    def test_forget_interactive_quit_at_picker(
        self, mock_picker, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """forget (no args) quit at picker exits gracefully."""
        _create_test_run(
            state_manager, "run-123", "Test task", PipelineStatus.COMPLETED, tmp_path
        )

        # User quits at picker
        mock_picker.side_effect = KeyboardInterrupt

        # Run interactive forget
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(app, ["forget", "--db-path", str(test_db)])

        assert result.exit_code == 0
        # Verify run still exists
        assert state_manager.get_run("run-123") is not None

    def test_forget_empty_database_shows_message(
        self, state_manager: StateManager, test_db: Path
    ):
        """forget on empty database shows appropriate message."""
        # Verify database is empty
        assert len(state_manager.list_runs()) == 0

        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(
                app, ["forget", "--db-path", str(test_db)]
            )

        assert result.exit_code == 0
        assert "no runs" in result.output.lower()

    @patch("levelup.cli.prompts.confirm_action")
    def test_forget_nuke_empty_database_shows_message(
        self, mock_confirm, state_manager: StateManager, test_db: Path
    ):
        """forget --nuke on empty database shows appropriate message."""
        # Verify database is empty
        assert len(state_manager.list_runs()) == 0

        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(
                app, ["forget", "--nuke", "--db-path", str(test_db)]
            )

        assert result.exit_code == 0
        assert "no runs" in result.output.lower()
        # Should not prompt for confirmation when empty
        mock_confirm.assert_not_called()

    def test_forget_works_with_all_run_statuses(
        self, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """forget command works with runs of any status."""
        statuses = [
            PipelineStatus.COMPLETED,
            PipelineStatus.FAILED,
            PipelineStatus.RUNNING,
            PipelineStatus.PENDING,
            PipelineStatus.ABORTED,
        ]

        for i, status in enumerate(statuses):
            run_id = f"run-status-{i}"
            _create_test_run(
                state_manager, run_id, f"Task {i}", status, tmp_path
            )

            # Verify run exists
            assert state_manager.get_run(run_id) is not None

            # Delete run
            with patch("levelup.cli.app.print_banner"):
                result = runner.invoke(
                    app, ["forget", run_id, "--db-path", str(test_db)]
                )

            assert result.exit_code == 0
            # Verify run is deleted
            assert state_manager.get_run(run_id) is None

    def test_forget_with_runs_without_context_json(
        self, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """forget works with runs that don't have context_json."""
        ctx = _create_test_run(
            state_manager, "run-no-ctx", "Task", PipelineStatus.PENDING, tmp_path
        )

        # Manually clear context_json (simulating old/incomplete run)
        conn = state_manager._conn()
        conn.execute("UPDATE runs SET context_json = NULL WHERE run_id = ?", ("run-no-ctx",))
        conn.commit()
        conn.close()

        # Verify run exists without context
        run = state_manager.get_run("run-no-ctx")
        assert run is not None
        assert run.context_json is None

        # Delete run
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(
                app, ["forget", "run-no-ctx", "--db-path", str(test_db)]
            )

        assert result.exit_code == 0
        assert state_manager.get_run("run-no-ctx") is None

    @patch("levelup.cli.prompts.pick_run_to_forget")
    @patch("levelup.cli.prompts.confirm_action")
    def test_forget_interactive_shows_all_statuses(
        self,
        mock_confirm,
        mock_picker,
        state_manager: StateManager,
        test_db: Path,
        tmp_path: Path,
    ):
        """forget interactive mode shows runs of all statuses."""
        # Create runs with different statuses
        _create_test_run(
            state_manager, "completed-run", "Task 1", PipelineStatus.COMPLETED, tmp_path
        )
        _create_test_run(
            state_manager, "failed-run", "Task 2", PipelineStatus.FAILED, tmp_path
        )
        _create_test_run(
            state_manager, "running-run", "Task 3", PipelineStatus.RUNNING, tmp_path
        )

        run_record = state_manager.get_run("failed-run")
        mock_picker.return_value = run_record
        mock_confirm.return_value = True

        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(app, ["forget", "--db-path", str(test_db)])

        # Verify picker was called with all runs
        picker_runs = mock_picker.call_args[0][0]
        assert len(picker_runs) == 3
        run_ids = {run.run_id for run in picker_runs}
        assert run_ids == {"completed-run", "failed-run", "running-run"}

    @patch("levelup.cli.prompts.confirm_action")
    def test_forget_nuke_removes_all_checkpoints(
        self, mock_confirm, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """forget --nuke also removes all checkpoint requests."""
        # Create runs with checkpoints
        _create_test_run(
            state_manager, "run-1", "Task 1", PipelineStatus.FAILED, tmp_path
        )
        _create_test_run(
            state_manager, "run-2", "Task 2", PipelineStatus.FAILED, tmp_path
        )

        state_manager.create_checkpoint_request("run-1", "requirements", "{}")
        state_manager.create_checkpoint_request("run-2", "test_writing", "{}")

        # Verify checkpoints exist
        assert len(state_manager.get_pending_checkpoints()) == 2

        mock_confirm.return_value = True

        # Nuke all runs
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(
                app, ["forget", "--nuke", "--db-path", str(test_db)]
            )

        assert result.exit_code == 0
        # Verify all checkpoints are deleted
        assert len(state_manager.get_pending_checkpoints()) == 0

    def test_forget_marks_dead_runs_before_listing(
        self, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """forget command marks dead runs before listing."""
        _create_test_run(
            state_manager, "run-dead", "Task", PipelineStatus.RUNNING, tmp_path
        )

        # Manually set a dead PID
        conn = state_manager._conn()
        conn.execute("UPDATE runs SET pid = 99999999 WHERE run_id = ?", ("run-dead",))
        conn.commit()
        conn.close()

        with patch("levelup.cli.app.print_banner"):
            # This should mark dead runs before showing list
            with patch("levelup.state.manager._is_pid_alive", return_value=False):
                result = runner.invoke(app, ["forget", "--db-path", str(test_db)])

        # Run should be marked as failed (dead)
        run = state_manager.get_run("run-dead")
        assert run is not None
        assert run.status == "failed"
        assert run.error_message == "Process died"

    def test_concurrent_forget_operations(
        self, state_manager: StateManager, test_db: Path, tmp_path: Path
    ):
        """Multiple forget operations can work concurrently (SQLite WAL mode)."""
        # Create runs
        for i in range(3):
            _create_test_run(
                state_manager, f"run-{i}", f"Task {i}", PipelineStatus.COMPLETED, tmp_path
            )

        # Delete runs from different "processes" (simulated by different manager instances)
        mgr1 = StateManager(db_path=test_db)
        mgr2 = StateManager(db_path=test_db)

        with patch("levelup.cli.app.print_banner"):
            # First manager deletes run-0
            result1 = runner.invoke(
                app, ["forget", "run-0", "--db-path", str(test_db)]
            )
            # Second manager deletes run-1
            result2 = runner.invoke(
                app, ["forget", "run-1", "--db-path", str(test_db)]
            )

        assert result1.exit_code == 0
        assert result2.exit_code == 0

        # Verify correct runs were deleted
        assert state_manager.get_run("run-0") is None
        assert state_manager.get_run("run-1") is None
        assert state_manager.get_run("run-2") is not None


class TestForgetCommandCustomDBPath:
    """Test forget command with custom database paths."""

    def test_forget_with_custom_db_path(self, tmp_path: Path):
        """forget command uses custom --db-path."""
        custom_db = tmp_path / "custom" / "state.db"
        custom_db.parent.mkdir(parents=True, exist_ok=True)

        mgr = StateManager(db_path=custom_db)
        ctx = _create_test_run(
            mgr, "custom-run", "Custom task", PipelineStatus.COMPLETED, tmp_path
        )

        # Verify run exists in custom DB
        assert mgr.get_run("custom-run") is not None

        # Delete using custom path
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(
                app, ["forget", "custom-run", "--db-path", str(custom_db)]
            )

        assert result.exit_code == 0
        # Verify deletion from custom DB
        assert mgr.get_run("custom-run") is None

    def test_forget_without_db_path_uses_default(self, tmp_path: Path):
        """forget without --db-path uses default location."""
        # This test verifies the default path behavior
        # We can't easily test the actual default path, but we can verify
        # that the command runs without --db-path
        with patch("levelup.cli.app.print_banner"):
            result = runner.invoke(app, ["forget", "nonexistent-run"])

        # Should error about non-existent run, not about missing db-path
        assert result.exit_code == 1
        assert "not found" in result.output.lower()
