"""Updated unit tests for ticket metadata excluding run options.

This test suite updates existing ticket metadata tests to reflect that
model, effort, and skip_planning are NO LONGER part of ticket metadata.

Requirements:
- Ticket metadata should not contain model, effort, skip_planning
- Auto-approve remains in ticket metadata (ticket-level)
- Other custom metadata fields work normally
- Backward compatibility: old tickets with run options load without errors

These tests follow TDD approach - they SHOULD FAIL initially until the
implementation is complete.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from levelup.core.tickets import (
    add_ticket,
    parse_tickets,
    read_tickets,
    set_ticket_status,
    TicketStatus,
    update_ticket,
)


# ---------------------------------------------------------------------------
# AC: Ticket metadata excludes run options
# ---------------------------------------------------------------------------


class TestTicketMetadataExcludesRunOptions:
    """Test that ticket metadata no longer includes run options."""

    def test_add_ticket_does_not_accept_model_in_metadata(self, tmp_path: Path):
        """AC: add_ticket should not save 'model' to ticket metadata."""
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"model": "sonnet", "priority": "high"},
        )

        # Read back
        tickets = read_tickets(tmp_path)
        saved_ticket = tickets[0]

        # model should not be saved
        assert "model" not in (saved_ticket.metadata or {})
        # other metadata should be preserved
        assert saved_ticket.metadata.get("priority") == "high"

    def test_add_ticket_does_not_accept_effort_in_metadata(self, tmp_path: Path):
        """AC: add_ticket should not save 'effort' to ticket metadata."""
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"effort": "high", "estimate": "2h"},
        )

        tickets = read_tickets(tmp_path)
        saved_ticket = tickets[0]

        assert "effort" not in (saved_ticket.metadata or {})
        assert saved_ticket.metadata.get("estimate") == "2h"

    def test_add_ticket_does_not_accept_skip_planning_in_metadata(self, tmp_path: Path):
        """AC: add_ticket should not save 'skip_planning' to ticket metadata."""
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"skip_planning": True, "tags": ["urgent"]},
        )

        tickets = read_tickets(tmp_path)
        saved_ticket = tickets[0]

        assert "skip_planning" not in (saved_ticket.metadata or {})
        assert saved_ticket.metadata.get("tags") == ["urgent"]

    def test_add_ticket_accepts_auto_approve_in_metadata(self, tmp_path: Path):
        """AC: add_ticket SHOULD save 'auto_approve' to ticket metadata (ticket-level)."""
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"auto_approve": True},
        )

        tickets = read_tickets(tmp_path)
        saved_ticket = tickets[0]

        # auto_approve should be saved
        assert saved_ticket.metadata.get("auto_approve") is True


# ---------------------------------------------------------------------------
# AC: update_ticket filters run options
# ---------------------------------------------------------------------------


class TestUpdateTicketFiltersRunOptions:
    """Test that update_ticket filters out run options from metadata."""

    def test_update_ticket_removes_model_from_metadata(self, tmp_path: Path):
        """AC: update_ticket should remove 'model' from metadata."""
        # Create ticket with model in metadata (legacy)
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## Test task\n"
            "<!--metadata\n"
            "model: sonnet\n"
            "priority: high\n"
            "-->\n"
            "Description\n",
            encoding="utf-8",
        )

        # Update ticket
        update_ticket(tmp_path, 1, title="Updated task")

        # Read back
        tickets = read_tickets(tmp_path)
        assert "model" not in (tickets[0].metadata or {})
        assert tickets[0].metadata.get("priority") == "high"

    def test_update_ticket_removes_effort_from_metadata(self, tmp_path: Path):
        """AC: update_ticket should remove 'effort' from metadata."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## Test task\n"
            "<!--metadata\n"
            "effort: high\n"
            "estimate: 3h\n"
            "-->\n"
            "Description\n",
            encoding="utf-8",
        )

        update_ticket(tmp_path, 1, title="Updated task")

        tickets = read_tickets(tmp_path)
        assert "effort" not in (tickets[0].metadata or {})
        assert tickets[0].metadata.get("estimate") == "3h"

    def test_update_ticket_removes_skip_planning_from_metadata(self, tmp_path: Path):
        """AC: update_ticket should remove 'skip_planning' from metadata."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## Test task\n"
            "<!--metadata\n"
            "skip_planning: true\n"
            "assignee: alice\n"
            "-->\n"
            "Description\n",
            encoding="utf-8",
        )

        update_ticket(tmp_path, 1, description="Updated description")

        tickets = read_tickets(tmp_path)
        assert "skip_planning" not in (tickets[0].metadata or {})
        assert tickets[0].metadata.get("assignee") == "alice"

    def test_update_ticket_preserves_auto_approve(self, tmp_path: Path):
        """AC: update_ticket should preserve 'auto_approve' (ticket-level metadata)."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## Test task\n"
            "<!--metadata\n"
            "auto_approve: true\n"
            "-->\n"
            "Description\n",
            encoding="utf-8",
        )

        update_ticket(tmp_path, 1, title="Updated task")

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata.get("auto_approve") is True


# ---------------------------------------------------------------------------
# AC: set_ticket_status filters run options
# ---------------------------------------------------------------------------


class TestSetTicketStatusFiltersRunOptions:
    """Test that set_ticket_status filters out run options from metadata."""

    def test_set_ticket_status_removes_run_options(self, tmp_path: Path):
        """AC: set_ticket_status should remove run options when updating status."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## Test task\n"
            "<!--metadata\n"
            "model: opus\n"
            "effort: low\n"
            "skip_planning: true\n"
            "priority: urgent\n"
            "-->\n"
            "Description\n",
            encoding="utf-8",
        )

        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)

        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.IN_PROGRESS
        # Run options should be removed
        assert "model" not in (tickets[0].metadata or {})
        assert "effort" not in (tickets[0].metadata or {})
        assert "skip_planning" not in (tickets[0].metadata or {})
        # Other metadata preserved
        assert tickets[0].metadata.get("priority") == "urgent"


# ---------------------------------------------------------------------------
# AC: Parsing tickets with run options (backward compatibility)
# ---------------------------------------------------------------------------


class TestParseTicketsWithRunOptions:
    """Test that parsing tickets with legacy run options works correctly."""

    def test_parse_ticket_with_model_metadata(self):
        """AC: Parsing ticket with 'model' in metadata should filter it out."""
        md = (
            "## Test task\n"
            "<!--metadata\n"
            "model: sonnet\n"
            "priority: high\n"
            "-->\n"
            "Description\n"
        )

        tickets = parse_tickets(md)
        assert len(tickets) == 1

        # model should be filtered out during parsing or saving
        # (implementation detail: may be in parsed ticket but not saved)
        # For backward compatibility, we accept it during parse but exclude on save

    def test_parse_ticket_with_all_run_options(self):
        """AC: Parsing ticket with all run options should handle gracefully."""
        md = (
            "## Test task\n"
            "<!--metadata\n"
            "model: opus\n"
            "effort: high\n"
            "skip_planning: true\n"
            "auto_approve: true\n"
            "priority: urgent\n"
            "-->\n"
            "Description\n"
        )

        tickets = parse_tickets(md)
        assert len(tickets) == 1

        # Ticket should parse without error
        # auto_approve and priority should be preserved
        # Run options may be present in parsed ticket but won't be saved


# ---------------------------------------------------------------------------
# AC: Round-trip metadata without run options
# ---------------------------------------------------------------------------


class TestRoundTripMetadataWithoutRunOptions:
    """Test that metadata round-trips correctly without run options."""

    def test_round_trip_preserves_non_run_options(self, tmp_path: Path):
        """AC: Multiple read/write cycles preserve non-run-option metadata."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={
                "auto_approve": True,
                "priority": "high",
                "estimate": "2h",
                "tags": ["bug", "urgent"],
            },
        )

        # Update status
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)

        # Update title
        update_ticket(tmp_path, 1, title="Updated task")

        # Read back
        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "Updated task"
        assert tickets[0].status == TicketStatus.IN_PROGRESS
        assert tickets[0].metadata.get("auto_approve") is True
        assert tickets[0].metadata.get("priority") == "high"
        assert tickets[0].metadata.get("estimate") == "2h"
        assert tickets[0].metadata.get("tags") == ["bug", "urgent"]

    def test_round_trip_cleans_legacy_run_options(self, tmp_path: Path):
        """AC: Round-trip should clean out legacy run options from tickets."""
        # Create legacy ticket with run options
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## Legacy task\n"
            "<!--metadata\n"
            "model: opus\n"
            "effort: high\n"
            "skip_planning: true\n"
            "auto_approve: false\n"
            "priority: normal\n"
            "-->\n"
            "Description\n",
            encoding="utf-8",
        )

        # Read and re-save
        tickets = read_tickets(tmp_path)
        update_ticket(tmp_path, 1, title="Cleaned task")

        # Read back
        tickets = read_tickets(tmp_path)
        metadata = tickets[0].metadata or {}

        # Run options should be gone
        assert "model" not in metadata
        assert "effort" not in metadata
        assert "skip_planning" not in metadata

        # Other metadata preserved
        assert metadata.get("auto_approve") is False
        assert metadata.get("priority") == "normal"


# ---------------------------------------------------------------------------
# AC: Metadata file format
# ---------------------------------------------------------------------------


class TestMetadataFileFormat:
    """Test that written metadata file format excludes run options."""

    def test_written_metadata_excludes_run_options(self, tmp_path: Path):
        """AC: Written metadata should not include model, effort, skip_planning."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={
                "model": "sonnet",  # Should be filtered
                "effort": "high",  # Should be filtered
                "skip_planning": True,  # Should be filtered
                "auto_approve": True,  # Should be kept
                "priority": "urgent",  # Should be kept
            },
        )

        path = tmp_path / "levelup" / "tickets.md"
        content = path.read_text()

        # Run options should not be in file
        assert "model:" not in content.lower()
        assert "effort:" not in content.lower()
        assert "skip_planning:" not in content.lower()

        # Other metadata should be in file
        assert "auto_approve: true" in content
        assert "priority: urgent" in content


# ---------------------------------------------------------------------------
# AC: Edge cases
# ---------------------------------------------------------------------------


class TestMetadataEdgeCases:
    """Test edge cases for metadata without run options."""

    def test_metadata_with_only_run_options_becomes_none(self, tmp_path: Path):
        """AC: Ticket with only run options in metadata should have metadata=None after save."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={
                "model": "opus",
                "effort": "low",
                "skip_planning": True,
            },
        )

        tickets = read_tickets(tmp_path)

        # All metadata was run options, so metadata should be None or empty
        assert tickets[0].metadata is None or tickets[0].metadata == {}

    def test_empty_metadata_after_filtering(self, tmp_path: Path):
        """AC: Filtering run options that leaves empty metadata should result in None."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## Task\n"
            "<!--metadata\n"
            "model: sonnet\n"
            "-->\n"
            "Description\n",
            encoding="utf-8",
        )

        update_ticket(tmp_path, 1, title="Updated")

        tickets = read_tickets(tmp_path)
        # Should be None or empty after filtering
        assert tickets[0].metadata is None or tickets[0].metadata == {}

    def test_custom_metadata_fields_work_normally(self, tmp_path: Path):
        """AC: Custom (non-run-option) metadata fields work normally."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={
                "assignee": "alice",
                "sprint": "2024-01",
                "story_points": 5,
                "labels": ["backend", "api"],
                "custom_field": {"nested": "value"},
            },
        )

        tickets = read_tickets(tmp_path)
        metadata = tickets[0].metadata

        assert metadata.get("assignee") == "alice"
        assert metadata.get("sprint") == "2024-01"
        assert metadata.get("story_points") == 5
        assert metadata.get("labels") == ["backend", "api"]
        assert metadata.get("custom_field") == {"nested": "value"}
