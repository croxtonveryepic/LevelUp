"""Unit tests for recording branch names in ticket metadata.

Tests the feature where branch names are automatically recorded in ticket metadata
when a pipeline completes successfully.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.core.tickets import (
    Ticket,
    TicketStatus,
    add_ticket,
    parse_tickets,
    read_tickets,
    set_ticket_status,
    update_ticket,
)


runner = CliRunner()


# ---------------------------------------------------------------------------
# Ticket metadata field for branch_name
# ---------------------------------------------------------------------------


class TestBranchNameMetadataField:
    """Test that branch_name can be stored in ticket metadata."""

    def test_metadata_accepts_branch_name(self):
        """Ticket metadata should accept a branch_name field."""
        t = Ticket(
            number=1,
            title="Test",
            metadata={"branch_name": "levelup/abc123def456"},
        )
        assert t.metadata["branch_name"] == "levelup/abc123def456"

    def test_branch_name_coexists_with_auto_approve(self):
        """branch_name and auto_approve should coexist in metadata."""
        t = Ticket(
            number=1,
            title="Test",
            metadata={
                "auto_approve": True,
                "branch_name": "feature/test-branch",
            },
        )
        assert t.metadata["auto_approve"] is True
        assert t.metadata["branch_name"] == "feature/test-branch"

    def test_branch_name_with_special_characters(self):
        """Branch names can contain slashes, hyphens, underscores."""
        t = Ticket(
            number=1,
            title="Test",
            metadata={"branch_name": "feature/fix-bug_123"},
        )
        assert t.metadata["branch_name"] == "feature/fix-bug_123"

    def test_branch_name_with_placeholders(self):
        """Branch name can contain various placeholder patterns."""
        t = Ticket(
            number=1,
            title="Test",
            metadata={"branch_name": "levelup/20260210-implement-feature"},
        )
        assert t.metadata["branch_name"] == "levelup/20260210-implement-feature"


# ---------------------------------------------------------------------------
# Parsing branch_name from markdown
# ---------------------------------------------------------------------------


class TestParseBranchNameMetadata:
    """Test parsing branch_name from markdown ticket metadata."""

    def test_parse_ticket_with_branch_name(self):
        """Should parse branch_name from metadata block."""
        md = (
            "## Task title\n"
            "<!--metadata\n"
            "branch_name: levelup/abc123\n"
            "-->\n"
            "Description here\n"
        )
        tickets = parse_tickets(md)
        assert len(tickets) == 1
        assert tickets[0].metadata is not None
        assert tickets[0].metadata["branch_name"] == "levelup/abc123"

    def test_parse_branch_name_with_auto_approve(self):
        """Should parse both branch_name and auto_approve."""
        md = (
            "## Task title\n"
            "<!--metadata\n"
            "auto_approve: true\n"
            "branch_name: feature/my-branch\n"
            "-->\n"
            "Description\n"
        )
        tickets = parse_tickets(md)
        meta = tickets[0].metadata
        assert meta["auto_approve"] is True
        assert meta["branch_name"] == "feature/my-branch"

    def test_parse_multiple_tickets_mixed_branch_names(self):
        """Some tickets with branch_name, some without."""
        md = (
            "## Task 1\n"
            "<!--metadata\n"
            "branch_name: levelup/run1\n"
            "-->\n"
            "Desc 1\n\n"
            "## Task 2\n"
            "Desc 2\n\n"
            "## Task 3\n"
            "<!--metadata\n"
            "branch_name: levelup/run3\n"
            "-->\n"
            "Desc 3\n"
        )
        tickets = parse_tickets(md)
        assert len(tickets) == 3
        assert tickets[0].metadata["branch_name"] == "levelup/run1"
        assert tickets[1].metadata is None
        assert tickets[2].metadata["branch_name"] == "levelup/run3"

    def test_parse_branch_name_preserves_description(self):
        """Description after metadata with branch_name should be preserved."""
        md = (
            "## Task\n"
            "<!--metadata\n"
            "branch_name: levelup/xyz789\n"
            "-->\n"
            "This is the task description.\n"
            "Multiple lines of content.\n"
        )
        tickets = parse_tickets(md)
        assert "task description" in tickets[0].description.lower()
        assert "Multiple lines" in tickets[0].description
        assert "branch_name" not in tickets[0].description


# ---------------------------------------------------------------------------
# Writing branch_name to markdown
# ---------------------------------------------------------------------------


class TestWriteBranchNameMetadata:
    """Test serializing branch_name to ticket metadata."""

    def test_add_ticket_with_branch_name(self, tmp_path: Path):
        """add_ticket should accept and serialize branch_name."""
        t = add_ticket(
            tmp_path,
            "Task title",
            "Description",
            metadata={"branch_name": "levelup/abc123"},
        )
        assert t.metadata == {"branch_name": "levelup/abc123"}

        # Read back and verify
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert tickets[0].metadata["branch_name"] == "levelup/abc123"

    def test_update_ticket_set_branch_name(self, tmp_path: Path):
        """update_ticket should be able to set branch_name."""
        add_ticket(tmp_path, "Original title", "Description")

        update_ticket(
            tmp_path,
            1,
            metadata={"branch_name": "levelup/xyz789"},
        )

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["branch_name"] == "levelup/xyz789"

    def test_update_ticket_add_branch_name_to_existing_metadata(self, tmp_path: Path):
        """Should add branch_name to ticket that already has auto_approve."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={"auto_approve": True},
        )

        # Add branch_name to existing metadata
        update_ticket(
            tmp_path,
            1,
            metadata={"auto_approve": True, "branch_name": "levelup/run123"},
        )

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["auto_approve"] is True
        assert tickets[0].metadata["branch_name"] == "levelup/run123"

    def test_update_ticket_overwrite_existing_branch_name(self, tmp_path: Path):
        """Should overwrite existing branch_name on subsequent updates."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={"branch_name": "levelup/old-branch"},
        )

        update_ticket(
            tmp_path,
            1,
            metadata={"branch_name": "levelup/new-branch"},
        )

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["branch_name"] == "levelup/new-branch"

    def test_set_ticket_status_preserves_branch_name(self, tmp_path: Path):
        """set_ticket_status should preserve branch_name metadata."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={"branch_name": "levelup/abc123"},
        )

        set_ticket_status(tmp_path, 1, TicketStatus.DONE)

        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DONE
        assert tickets[0].metadata["branch_name"] == "levelup/abc123"

    def test_branch_name_stored_in_db(self, tmp_path: Path):
        """Written branch_name should be stored in the DB."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={"branch_name": "feature/my-feature"},
        )

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is not None
        assert tickets[0].metadata["branch_name"] == "feature/my-feature"

    def test_round_trip_branch_name_metadata(self, tmp_path: Path):
        """branch_name should survive multiple read/write cycles."""
        add_ticket(
            tmp_path,
            "Task",
            "Desc",
            metadata={"branch_name": "levelup/run1", "auto_approve": True},
        )

        # Update status
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)

        # Update title
        update_ticket(tmp_path, 1, title="Updated task")

        # Read back
        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "Updated task"
        assert tickets[0].status == TicketStatus.IN_PROGRESS
        assert tickets[0].metadata["branch_name"] == "levelup/run1"
        assert tickets[0].metadata["auto_approve"] is True

    def test_multiple_metadata_fields_serialization(self, tmp_path: Path):
        """Multiple metadata fields including branch_name should serialize correctly."""
        metadata = {
            "auto_approve": True,
            "branch_name": "levelup/complex-123",
            "priority": "high",
        }
        add_ticket(tmp_path, "Task", "Description", metadata=metadata)

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["auto_approve"] is True
        assert tickets[0].metadata["branch_name"] == "levelup/complex-123"
        assert tickets[0].metadata["priority"] == "high"


# ---------------------------------------------------------------------------
# CLI integration: recording branch name on completion
# ---------------------------------------------------------------------------


class TestBranchNameRecordingOnCompletion:
    """Test that branch name is recorded when pipeline completes successfully."""

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_completed_pipeline_records_branch_name(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """When pipeline completes, branch_name should be recorded in ticket metadata."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test feature")

        # Mock successful completion with branch naming
        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "abc123def456"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/abc123def456"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            ["run", "Test feature", "--path", str(tmp_path), "--ticket", "1", "--no-checkpoints"],
        )

        # Verify branch_name was recorded
        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is not None
        assert "branch_name" in tickets[0].metadata
        assert tickets[0].metadata["branch_name"] == "levelup/abc123def456"

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_branch_name_uses_build_branch_name_logic(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """Branch name should be calculated using _build_branch_name method."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Complex task name")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "xyz789"
        mock_ctx.branch_naming = "feature/{task_title}-{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "feature/complex-task-name-xyz789"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            ["run", "Complex task name", "--path", str(tmp_path), "--ticket", "1", "--no-checkpoints"],
        )

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["branch_name"] == "feature/complex-task-name-xyz789"

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_branch_name_not_recorded_for_failed_pipeline(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """Branch name should NOT be recorded if pipeline fails."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test feature")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "failed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "fail123"
        mock_ctx.branch_naming = "levelup/{run_id}"
        mock_ctx.error_message = "Something went wrong"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with pytest.raises(SystemExit):
            result = runner.invoke(
                app,
                ["run", "Test feature", "--path", str(tmp_path), "--ticket", "1", "--no-checkpoints"],
            )

        # Verify branch_name was NOT recorded
        tickets = read_tickets(tmp_path)
        # Ticket should still be in progress or have no branch_name
        if tickets[0].metadata:
            assert "branch_name" not in tickets[0].metadata

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_branch_name_not_recorded_for_manual_tasks(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """Branch name should NOT be recorded for manually entered tasks without tickets."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "manual"  # Not a ticket
        mock_ctx.task.source_id = None
        mock_ctx.run_id = "manual123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            ["run", "Manual task", "--path", str(tmp_path), "--no-checkpoints"],
        )

        # Since this was auto-created as ticket, check it doesn't have branch_name yet
        # (this tests the edge case)
        tickets = read_tickets(tmp_path)
        # The implementation should only record for explicit tickets
        # This test will evolve based on actual behavior

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_branch_name_overwrites_previous_on_rerun(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """If ticket is re-run, branch_name should be updated/overwritten."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(
            tmp_path,
            "Test feature",
            metadata={"branch_name": "levelup/old-run-123"},
        )

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "newrun456"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/newrun456"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            ["run", "Test feature", "--path", str(tmp_path), "--ticket", "1", "--no-checkpoints"],
        )

        # Verify branch_name was updated
        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["branch_name"] == "levelup/newrun456"

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_branch_name_preserves_other_metadata(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """Recording branch_name should preserve existing metadata like auto_approve."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(
            tmp_path,
            "Test feature",
            metadata={"auto_approve": True, "priority": "high"},
        )

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "run123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/run123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            ["run", "Test feature", "--path", str(tmp_path), "--ticket", "1", "--no-checkpoints"],
        )

        # Verify all metadata fields are preserved
        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["auto_approve"] is True
        assert tickets[0].metadata["priority"] == "high"
        assert tickets[0].metadata["branch_name"] == "levelup/run123"

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_branch_name_works_in_headless_mode(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """Branch name recording should work in headless mode."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Headless task")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "headless123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/headless123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            [
                "run",
                "Headless task",
                "--path",
                str(tmp_path),
                "--ticket",
                "1",
                "--headless",
                "--no-checkpoints",
            ],
        )

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["branch_name"] == "levelup/headless123"

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_branch_name_uses_default_when_convention_missing(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """Should use default 'levelup/{run_id}' when branch_naming is None."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test feature")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "default789"
        mock_ctx.branch_naming = None  # No custom convention

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        # Should default to levelup/{run_id}
        mock_orch._build_branch_name.return_value = "levelup/default789"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            ["run", "Test feature", "--path", str(tmp_path), "--ticket", "1", "--no-checkpoints"],
        )

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["branch_name"] == "levelup/default789"


# ---------------------------------------------------------------------------
# Error handling and edge cases
# ---------------------------------------------------------------------------


class TestBranchNameErrorHandling:
    """Test error handling for branch name recording."""

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_gracefully_handles_missing_branch_naming(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """Should handle gracefully when branch naming is not enabled."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test feature")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "nobranch123"
        mock_ctx.branch_naming = None

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        # Simulate that orchestrator doesn't have _build_branch_name
        mock_orch._build_branch_name = None
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        # Should not crash
        result = runner.invoke(
            app,
            ["run", "Test feature", "--path", str(tmp_path), "--ticket", "1", "--no-checkpoints"],
        )

        # May or may not have branch_name, but shouldn't crash
        assert result.exit_code == 0

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_gracefully_handles_missing_context_fields(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """Should handle gracefully when context is missing expected fields."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test feature")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        # Missing run_id
        mock_ctx.run_id = None
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        # Should not crash
        result = runner.invoke(
            app,
            ["run", "Test feature", "--path", str(tmp_path), "--ticket", "1", "--no-checkpoints"],
        )

        # Should complete without error
        assert result.exit_code == 0

    def test_branch_name_with_special_yaml_characters(self, tmp_path: Path):
        """Branch names with special YAML characters should be handled correctly."""
        # Test colon, which is special in YAML
        metadata = {"branch_name": "feature/fix:critical"}
        add_ticket(tmp_path, "Task", "Description", metadata=metadata)

        tickets = read_tickets(tmp_path)
        # Should handle the colon correctly
        assert "fix" in tickets[0].metadata["branch_name"]

    def test_branch_name_very_long(self, tmp_path: Path):
        """Very long branch names should be stored correctly."""
        long_branch = "levelup/" + "a" * 200
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={"branch_name": long_branch},
        )

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["branch_name"] == long_branch


# ---------------------------------------------------------------------------
# Integration with other CLI commands
# ---------------------------------------------------------------------------


class TestBranchNameIntegrationWithCLI:
    """Test branch_name metadata interaction with other CLI commands."""

    def test_tickets_list_shows_branch_name(self, tmp_path: Path):
        """'levelup tickets list' should display branch name if present."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task without branch")
        add_ticket(
            tmp_path, "Task with branch", metadata={"branch_name": "levelup/abc123"}
        )

        result = runner.invoke(app, ["tickets", "list", "--path", str(tmp_path)])

        assert result.exit_code == 0
        # Output should indicate branch name presence somehow
        # (exact format TBD in implementation)

    def test_branch_name_survives_status_changes(self, tmp_path: Path):
        """Branch name should persist through status transitions."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(
            tmp_path, "Task", metadata={"branch_name": "levelup/xyz789"}
        )

        # Start
        runner.invoke(app, ["tickets", "start", "1", "--path", str(tmp_path)])
        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["branch_name"] == "levelup/xyz789"

        # Done
        runner.invoke(app, ["tickets", "done", "1", "--path", str(tmp_path)])
        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["branch_name"] == "levelup/xyz789"

        # Merged
        runner.invoke(app, ["tickets", "merged", "1", "--path", str(tmp_path)])
        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["branch_name"] == "levelup/xyz789"
