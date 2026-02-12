"""Tests for CLI app.py — auto-ticket creation and duplicate run guard."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app


runner = CliRunner()


class TestAutoTicketCreation:
    """When a bare task string is given, a ticket should be auto-created."""

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_bare_task_creates_ticket(self, mock_sm_cls, mock_orch_cls, tmp_path):
        """levelup run 'some task' should create a ticket and print its number."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(app, [
            "run", "add login feature",
            "--path", str(tmp_path),
            "--no-checkpoints",
        ])

        assert result.exit_code == 0
        assert "Created ticket #1" in result.output

        # Verify ticket was created in DB
        from levelup.core.tickets import read_tickets
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert "add login feature" in tickets[0].title

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_bare_task_input_is_ticket_sourced(self, mock_sm_cls, mock_orch_cls, tmp_path):
        """The TaskInput passed to orchestrator should have source='ticket'."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(app, [
            "run", "some task",
            "--path", str(tmp_path),
            "--no-checkpoints",
        ])

        assert result.exit_code == 0
        # Check the TaskInput passed to orchestrator.run()
        call_args = mock_orch_cls.return_value.run.call_args
        task_input = call_args[0][0]
        assert task_input.source == "ticket"
        assert task_input.source_id.startswith("ticket:")


class TestDuplicateRunGuard:
    """When a ticket already has an active run, the CLI should refuse to start another."""

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_active_run_blocks_new_run(self, mock_sm_cls, mock_orch_cls, tmp_path):
        """Should exit with error if ticket already has an active run."""
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "existing task")

        # Mock state manager returning an active run
        mock_active = MagicMock()
        mock_active.run_id = "existing-run-id-1234"
        mock_active.status = "running"
        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = mock_active
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(app, [
            "run", "--ticket", "1",
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 1
        assert "already has an active run" in result.output

        # Orchestrator should NOT have been called
        mock_orch_cls.return_value.run.assert_not_called()

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_no_active_run_allows_new_run(self, mock_sm_cls, mock_orch_cls, tmp_path):
        """Should proceed when no active run exists for the ticket."""
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "new task")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(app, [
            "run", "--ticket", "1",
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        mock_orch_cls.return_value.run.assert_called_once()
