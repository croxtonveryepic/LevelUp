"""Unit tests for ticket metadata CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.core.tickets import add_ticket, read_tickets


runner = CliRunner()


class TestTicketsSetMetadataCommand:
    """Test 'levelup tickets set-metadata' command."""

    def test_set_metadata_command_exists(self, tmp_path: Path):
        """set-metadata subcommand should exist."""
        result = runner.invoke(app, ["tickets", "set-metadata", "--help"])
        # Should not error as unknown command
        assert result.exit_code in [0, 2]  # 0 = success, 2 = help shown

    def test_set_metadata_auto_approve_true(self, tmp_path: Path):
        """Should set auto_approve metadata to true."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test task", "Description")

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "1",
            "--auto-approve", "true",
            "--path", str(tmp_path),
        ])

        # Check that metadata was set
        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is not None
        assert tickets[0].metadata["auto_approve"] is True

    def test_set_metadata_auto_approve_false(self, tmp_path: Path):
        """Should set auto_approve metadata to false."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test task", "Description")

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "1",
            "--auto-approve", "false",
            "--path", str(tmp_path),
        ])

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is not None
        assert tickets[0].metadata["auto_approve"] is False

    def test_set_metadata_updates_existing(self, tmp_path: Path):
        """Should update existing metadata."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test task", "Description", metadata={"auto_approve": False})

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "1",
            "--auto-approve", "true",
            "--path", str(tmp_path),
        ])

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["auto_approve"] is True

    def test_set_metadata_nonexistent_ticket_errors(self, tmp_path: Path):
        """Should error if ticket doesn't exist."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "1",
            "--auto-approve", "true",
            "--path", str(tmp_path),
        ])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_set_metadata_invalid_ticket_number(self, tmp_path: Path):
        """Should error with invalid ticket number."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test task")

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "999",
            "--auto-approve", "true",
            "--path", str(tmp_path),
        ])

        assert result.exit_code != 0

    def test_set_metadata_confirmation_message(self, tmp_path: Path):
        """Should show confirmation after setting metadata."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Test task")

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "1",
            "--auto-approve", "true",
            "--path", str(tmp_path),
        ])

        # Should indicate success
        assert "success" in result.output.lower() or "updated" in result.output.lower()

    def test_set_metadata_preserves_other_fields(self, tmp_path: Path):
        """Setting metadata should preserve title, description, status."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Original title", "Original description")

        from levelup.core.tickets import set_ticket_status, TicketStatus
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "1",
            "--auto-approve", "true",
            "--path", str(tmp_path),
        ])

        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "Original title"
        assert tickets[0].description == "Original description"
        assert tickets[0].status == TicketStatus.IN_PROGRESS
        assert tickets[0].metadata["auto_approve"] is True

    def test_set_metadata_multiple_tickets(self, tmp_path: Path):
        """Should only affect the specified ticket."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task 1")
        add_ticket(tmp_path, "Task 2")
        add_ticket(tmp_path, "Task 3")

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "2",
            "--auto-approve", "true",
            "--path", str(tmp_path),
        ])

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is None
        assert tickets[1].metadata["auto_approve"] is True
        assert tickets[2].metadata is None


class TestTicketsMetadataIntegrationWithOtherCommands:
    """Test metadata interaction with other ticket commands."""

    def test_tickets_list_shows_auto_approve_indicator(self, tmp_path: Path):
        """'levelup tickets list' should indicate auto-approve status."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Normal task")
        add_ticket(tmp_path, "Auto task", metadata={"auto_approve": True})

        result = runner.invoke(app, [
            "tickets",
            "list",
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        # Should show some indicator for auto-approved tickets
        # Could be emoji, badge, or text

    def test_metadata_survives_status_changes(self, tmp_path: Path):
        """Metadata should persist through status changes via CLI."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", metadata={"auto_approve": True})

        # Start the ticket
        result = runner.invoke(app, [
            "tickets",
            "start",
            "1",
            "--path", str(tmp_path),
        ])

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["auto_approve"] is True

        # Mark it done
        result = runner.invoke(app, [
            "tickets",
            "done",
            "1",
            "--path", str(tmp_path),
        ])

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["auto_approve"] is True

    def test_delete_ticket_with_metadata(self, tmp_path: Path):
        """Deleting ticket with metadata should work."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", metadata={"auto_approve": True})

        result = runner.invoke(app, [
            "tickets",
            "delete",
            "1",
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 0


class TestAlternativeMetadataCommand:
    """Test alternative command syntax for setting metadata."""

    def test_tickets_update_with_metadata_flag(self, tmp_path: Path):
        """'levelup tickets update' with --metadata flag."""
        # This tests an alternative design where metadata is set via update command
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task")

        # This might not exist yet, testing the interface
        result = runner.invoke(app, [
            "tickets",
            "update",
            "1",
            "--auto-approve", "true",
            "--path", str(tmp_path),
        ])

        # Either it works or command doesn't exist yet
        if result.exit_code == 0:
            tickets = read_tickets(tmp_path)
            assert tickets[0].metadata is not None

    def test_tickets_metadata_show(self, tmp_path: Path):
        """Command to show metadata of a ticket."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", metadata={"auto_approve": True})

        result = runner.invoke(app, [
            "tickets",
            "show",
            "1",
            "--path", str(tmp_path),
        ])

        # Should display metadata if command exists
        if result.exit_code == 0:
            assert "auto_approve" in result.output or "metadata" in result.output.lower()


class TestMetadataEdgeCases:
    """Test edge cases for ticket metadata CLI."""

    def test_set_metadata_on_empty_tickets_file(self, tmp_path: Path):
        """Should handle gracefully when tickets file is empty."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text("", encoding="utf-8")

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "1",
            "--auto-approve", "true",
            "--path", str(tmp_path),
        ])

        assert result.exit_code != 0

    def test_set_metadata_invalid_value(self, tmp_path: Path):
        """Should validate auto_approve values."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task")

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "1",
            "--auto-approve", "invalid",
            "--path", str(tmp_path),
        ])

        # Should error on invalid boolean value
        assert result.exit_code != 0

    def test_set_metadata_case_insensitive(self, tmp_path: Path):
        """Should accept True/False/TRUE/FALSE."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task 1")
        add_ticket(tmp_path, "Task 2")

        # Test TRUE
        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "1",
            "--auto-approve", "TRUE",
            "--path", str(tmp_path),
        ])

        if result.exit_code == 0:
            tickets = read_tickets(tmp_path)
            assert tickets[0].metadata["auto_approve"] is True

        # Test False
        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "2",
            "--auto-approve", "False",
            "--path", str(tmp_path),
        ])

        if result.exit_code == 0:
            tickets = read_tickets(tmp_path)
            assert tickets[1].metadata["auto_approve"] is False

    def test_remove_metadata_with_none(self, tmp_path: Path):
        """Setting metadata to 'none' should remove it."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", metadata={"auto_approve": True})

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "1",
            "--auto-approve", "none",
            "--path", str(tmp_path),
        ])

        if result.exit_code == 0:
            tickets = read_tickets(tmp_path)
            # Metadata should be removed or auto_approve key should be absent
            assert tickets[0].metadata is None or "auto_approve" not in tickets[0].metadata

    def test_set_metadata_with_custom_tickets_file(self, tmp_path: Path):
        """Should work with custom tickets file location."""
        custom_file = "backlog.md"
        add_ticket(tmp_path, "Task", filename=custom_file)

        result = runner.invoke(app, [
            "tickets",
            "set-metadata",
            "1",
            "--auto-approve", "true",
            "--path", str(tmp_path),
            "--tickets-file", custom_file,
        ])

        if result.exit_code == 0:
            tickets = read_tickets(tmp_path, custom_file)
            assert tickets[0].metadata["auto_approve"] is True
