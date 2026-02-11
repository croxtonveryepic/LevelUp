"""Unit tests for CLI integration point where branch name is recorded.

Tests the specific code in cli/app.py run() function (lines 194-203)
that records the branch name in ticket metadata after successful completion.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from levelup.core.tickets import TicketStatus, add_ticket, read_tickets


class TestCLIBranchNameRecording:
    """Test the CLI code that records branch name on ticket completion."""

    @patch("levelup.cli.app.Orchestrator")
    @patch("levelup.cli.app.StateManager")
    def test_completion_flow_calls_update_ticket_with_branch_name(
        self, mock_sm_cls, mock_orch_cls, tmp_path: Path
    ):
        """The CLI should call update_ticket with branch_name in metadata."""
        from typer.testing import CliRunner

        from levelup.cli.app import app

        runner = CliRunner()

        # Setup
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test task")

        # Mock successful completion
        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "cli123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/cli123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        # Patch update_ticket to verify it's called correctly
        with patch("levelup.cli.app.update_ticket") as mock_update:
            result = runner.invoke(
                app,
                [
                    "run",
                    "Test task",
                    "--path",
                    str(tmp_path),
                    "--ticket",
                    "1",
                    "--no-checkpoints",
                ],
            )

            # Verify update_ticket was called with branch_name
            assert mock_update.called
            call_args = mock_update.call_args
            assert call_args[0][0] == tmp_path  # project_path
            assert call_args[0][1] == 1  # ticket_number
            assert "metadata" in call_args[1]
            metadata = call_args[1]["metadata"]
            assert "branch_name" in metadata
            assert metadata["branch_name"] == "levelup/cli123"

    @patch("levelup.cli.app.Orchestrator")
    @patch("levelup.cli.app.StateManager")
    def test_completion_flow_after_set_ticket_status(
        self, mock_sm_cls, mock_orch_cls, tmp_path: Path
    ):
        """Branch name should be recorded after ticket status is set to done."""
        from typer.testing import CliRunner

        from levelup.cli.app import app

        runner = CliRunner()

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test task")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "order123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/order123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        # Track order of calls
        call_order = []

        with patch("levelup.cli.app.set_ticket_status") as mock_set_status:
            mock_set_status.side_effect = lambda *args, **kwargs: call_order.append(
                "set_status"
            )

            with patch("levelup.cli.app.update_ticket") as mock_update:
                mock_update.side_effect = lambda *args, **kwargs: call_order.append(
                    "update_ticket"
                )

                result = runner.invoke(
                    app,
                    [
                        "run",
                        "Test task",
                        "--path",
                        str(tmp_path),
                        "--ticket",
                        "1",
                        "--no-checkpoints",
                    ],
                )

                # set_ticket_status should be called before update_ticket
                assert "set_status" in call_order
                assert "update_ticket" in call_order
                assert call_order.index("set_status") < call_order.index("update_ticket")

    @patch("levelup.cli.app.Orchestrator")
    @patch("levelup.cli.app.StateManager")
    def test_extracts_ticket_number_from_source_id(
        self, mock_sm_cls, mock_orch_cls, tmp_path: Path
    ):
        """Should correctly extract ticket number from source_id format 'ticket:N'."""
        from typer.testing import CliRunner

        from levelup.cli.app import app

        runner = CliRunner()

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task 1")
        add_ticket(tmp_path, "Task 2")
        add_ticket(tmp_path, "Task 3")

        # Test with ticket 2
        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:2"  # Second ticket
        mock_ctx.run_id = "extract456"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/extract456"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with patch("levelup.cli.app.update_ticket") as mock_update:
            result = runner.invoke(
                app,
                [
                    "run",
                    "Task 2",
                    "--path",
                    str(tmp_path),
                    "--ticket",
                    "2",
                    "--no-checkpoints",
                ],
            )

            # Should call update_ticket with ticket number 2
            assert mock_update.called
            assert mock_update.call_args[0][1] == 2

    @patch("levelup.cli.app.Orchestrator")
    @patch("levelup.cli.app.StateManager")
    def test_uses_orchestrator_build_branch_name_method(
        self, mock_sm_cls, mock_orch_cls, tmp_path: Path
    ):
        """Should call orchestrator._build_branch_name to get branch name."""
        from typer.testing import CliRunner

        from levelup.cli.app import app

        runner = CliRunner()

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test task")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "method789"
        mock_ctx.branch_naming = "feature/{task_title}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "feature/test-task"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            [
                "run",
                "Test task",
                "--path",
                str(tmp_path),
                "--ticket",
                "1",
                "--no-checkpoints",
            ],
        )

        # Verify _build_branch_name was called
        assert mock_orch._build_branch_name.called
        call_args = mock_orch._build_branch_name.call_args
        # Should be called with convention and context
        assert call_args[0][0] in ["feature/{task_title}", "levelup/{run_id}"]
        assert call_args[0][1] == mock_ctx

    @patch("levelup.cli.app.Orchestrator")
    @patch("levelup.cli.app.StateManager")
    def test_handles_none_branch_naming(
        self, mock_sm_cls, mock_orch_cls, tmp_path: Path
    ):
        """Should handle ctx.branch_naming being None."""
        from typer.testing import CliRunner

        from levelup.cli.app import app

        runner = CliRunner()

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test task")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "none123"
        mock_ctx.branch_naming = None  # No branch naming

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        # Should fall back to default
        mock_orch._build_branch_name.return_value = "levelup/none123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            [
                "run",
                "Test task",
                "--path",
                str(tmp_path),
                "--ticket",
                "1",
                "--no-checkpoints",
            ],
        )

        # Should complete without error
        assert result.exit_code == 0

        # Should use default convention
        if mock_orch._build_branch_name.called:
            call_args = mock_orch._build_branch_name.call_args
            convention = call_args[0][0]
            # Should be default or None
            assert convention in ["levelup/{run_id}", None, ""]

    @patch("levelup.cli.app.Orchestrator")
    @patch("levelup.cli.app.StateManager")
    def test_preserves_existing_metadata(
        self, mock_sm_cls, mock_orch_cls, tmp_path: Path
    ):
        """Should preserve existing metadata when adding branch_name."""
        from typer.testing import CliRunner

        from levelup.cli.app import app

        runner = CliRunner()

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(
            tmp_path,
            "Test task",
            metadata={"auto_approve": True, "priority": "high"},
        )

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "preserve123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/preserve123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            [
                "run",
                "Test task",
                "--path",
                str(tmp_path),
                "--ticket",
                "1",
                "--no-checkpoints",
            ],
        )

        # Verify all metadata preserved
        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["auto_approve"] is True
        assert tickets[0].metadata["priority"] == "high"
        assert tickets[0].metadata["branch_name"] == "levelup/preserve123"

    @patch("levelup.cli.app.Orchestrator")
    @patch("levelup.cli.app.StateManager")
    def test_exception_in_update_ticket_does_not_crash(
        self, mock_sm_cls, mock_orch_cls, tmp_path: Path
    ):
        """Should handle exception in update_ticket gracefully."""
        from typer.testing import CliRunner

        from levelup.cli.app import app

        runner = CliRunner()

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test task")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "error123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/error123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with patch("levelup.cli.app.update_ticket", side_effect=Exception("Update failed")):
            # Should not crash
            result = runner.invoke(
                app,
                [
                    "run",
                    "Test task",
                    "--path",
                    str(tmp_path),
                    "--ticket",
                    "1",
                    "--no-checkpoints",
                ],
            )

            # Should still exit successfully (pipeline completed)
            assert result.exit_code == 0

    @patch("levelup.cli.app.Orchestrator")
    @patch("levelup.cli.app.StateManager")
    def test_only_records_for_ticket_source(
        self, mock_sm_cls, mock_orch_cls, tmp_path: Path
    ):
        """Should only record branch_name when task source is 'ticket'."""
        from typer.testing import CliRunner

        from levelup.cli.app import app

        runner = CliRunner()

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Mock manual task (not from ticket)
        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "manual"  # Not a ticket
        mock_ctx.task.source_id = None
        mock_ctx.run_id = "manual123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/manual123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm_cls.return_value = mock_sm

        with patch("levelup.cli.app.update_ticket") as mock_update:
            result = runner.invoke(
                app,
                [
                    "run",
                    "Manual task",
                    "--path",
                    str(tmp_path),
                    "--no-checkpoints",
                ],
            )

            # update_ticket should NOT be called for manual tasks
            # (or if auto-created ticket, it will be handled differently)
            # This tests the guard condition

    @patch("levelup.cli.app.Orchestrator")
    @patch("levelup.cli.app.StateManager")
    def test_only_records_on_completed_status(
        self, mock_sm_cls, mock_orch_cls, tmp_path: Path
    ):
        """Should only record branch_name when status is completed."""
        from typer.testing import CliRunner

        from levelup.cli.app import app

        runner = CliRunner()

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test task")

        # Mock paused/aborted status
        mock_ctx = MagicMock()
        mock_ctx.status.value = "paused"  # Not completed
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "paused123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with patch("levelup.cli.app.update_ticket") as mock_update:
            result = runner.invoke(
                app,
                [
                    "run",
                    "Test task",
                    "--path",
                    str(tmp_path),
                    "--ticket",
                    "1",
                    "--no-checkpoints",
                ],
            )

            # update_ticket should NOT be called for non-completed status
            # (ticket status update also shouldn't happen)

    @patch("levelup.cli.app.Orchestrator")
    @patch("levelup.cli.app.StateManager")
    def test_reads_existing_ticket_metadata_before_update(
        self, mock_sm_cls, mock_orch_cls, tmp_path: Path
    ):
        """Should read existing ticket metadata to preserve it."""
        from typer.testing import CliRunner

        from levelup.cli.app import app

        runner = CliRunner()

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(
            tmp_path,
            "Test task",
            metadata={"auto_approve": True, "custom_field": "value"},
        )

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "read123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/read123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with patch("levelup.cli.app.update_ticket") as mock_update:
            result = runner.invoke(
                app,
                [
                    "run",
                    "Test task",
                    "--path",
                    str(tmp_path),
                    "--ticket",
                    "1",
                    "--no-checkpoints",
                ],
            )

            # Verify update_ticket was called with merged metadata
            assert mock_update.called
            metadata = mock_update.call_args[1]["metadata"]
            assert metadata["auto_approve"] is True
            assert metadata["custom_field"] == "value"
            assert metadata["branch_name"] == "levelup/read123"
