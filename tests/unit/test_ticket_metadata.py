"""Unit tests for ticket metadata parsing and serialization."""

from __future__ import annotations

from pathlib import Path

import pytest

from levelup.core.tickets import (
    Ticket,
    TicketStatus,
    add_ticket,
    delete_ticket,
    parse_tickets,
    read_tickets,
    set_ticket_status,
    update_ticket,
)


# ---------------------------------------------------------------------------
# Ticket metadata field
# ---------------------------------------------------------------------------


class TestTicketMetadata:
    """Test metadata field on Ticket model."""

    def test_ticket_has_metadata_field(self):
        """Ticket should have an optional metadata field."""
        t = Ticket(number=1, title="Test", metadata=None)
        assert hasattr(t, "metadata")
        assert t.metadata is None

    def test_metadata_defaults_to_none(self):
        """Metadata should default to None when not provided."""
        t = Ticket(number=1, title="Test")
        assert t.metadata is None

    def test_metadata_can_be_dict(self):
        """Metadata should accept a dict."""
        t = Ticket(number=1, title="Test", metadata={"auto_approve": True})
        assert t.metadata == {"auto_approve": True}

    def test_metadata_auto_approve_true(self):
        """Metadata can contain auto_approve: True."""
        t = Ticket(number=1, title="Test", metadata={"auto_approve": True})
        assert t.metadata["auto_approve"] is True

    def test_metadata_auto_approve_false(self):
        """Metadata can contain auto_approve: False."""
        t = Ticket(number=1, title="Test", metadata={"auto_approve": False})
        assert t.metadata["auto_approve"] is False

    def test_metadata_multiple_fields(self):
        """Metadata can contain multiple fields."""
        t = Ticket(
            number=1,
            title="Test",
            metadata={"auto_approve": True, "priority": "high"},
        )
        assert t.metadata["auto_approve"] is True
        assert t.metadata["priority"] == "high"


# ---------------------------------------------------------------------------
# Parsing metadata from markdown (HTML comment format)
# ---------------------------------------------------------------------------


class TestParseTicketMetadata:
    """Test parsing metadata from markdown tickets."""

    def test_parse_ticket_without_metadata(self):
        """Ticket without metadata should have metadata=None."""
        md = "## Task title\nDescription here\n"
        tickets = parse_tickets(md)
        assert len(tickets) == 1
        assert tickets[0].metadata is None

    def test_parse_ticket_with_metadata_block(self):
        """Ticket with metadata HTML comment should parse metadata."""
        md = (
            "## Task title\n"
            "<!--metadata\n"
            "auto_approve: true\n"
            "-->\n"
            "Description here\n"
        )
        tickets = parse_tickets(md)
        assert len(tickets) == 1
        assert tickets[0].metadata is not None
        assert tickets[0].metadata["auto_approve"] is True

    def test_parse_metadata_auto_approve_false(self):
        """Metadata with auto_approve: false should parse correctly."""
        md = (
            "## Task title\n"
            "<!--metadata\n"
            "auto_approve: false\n"
            "-->\n"
            "Description\n"
        )
        tickets = parse_tickets(md)
        assert tickets[0].metadata["auto_approve"] is False

    def test_parse_metadata_multiple_fields(self):
        """Metadata with multiple fields should parse all fields."""
        md = (
            "## Task title\n"
            "<!--metadata\n"
            "auto_approve: true\n"
            "priority: high\n"
            "estimate: 3h\n"
            "-->\n"
            "Description\n"
        )
        tickets = parse_tickets(md)
        meta = tickets[0].metadata
        assert meta["auto_approve"] is True
        assert meta["priority"] == "high"
        assert meta["estimate"] == "3h"

    def test_parse_preserves_description_after_metadata(self):
        """Description after metadata block should be preserved."""
        md = (
            "## Task title\n"
            "<!--metadata\n"
            "auto_approve: true\n"
            "-->\n"
            "This is the description.\n"
            "Multiple lines.\n"
        )
        tickets = parse_tickets(md)
        assert "This is the description" in tickets[0].description
        assert "Multiple lines" in tickets[0].description
        assert "metadata" not in tickets[0].description.lower()

    def test_parse_metadata_with_whitespace(self):
        """Metadata parsing should handle extra whitespace."""
        md = (
            "## Task title\n"
            "<!--metadata\n"
            "  auto_approve:   true  \n"
            "-->\n"
            "Description\n"
        )
        tickets = parse_tickets(md)
        assert tickets[0].metadata["auto_approve"] is True

    def test_parse_multiple_tickets_with_mixed_metadata(self):
        """Some tickets with metadata, some without."""
        md = (
            "## Task 1\n"
            "<!--metadata\n"
            "auto_approve: true\n"
            "-->\n"
            "Desc 1\n\n"
            "## Task 2\n"
            "Desc 2\n\n"
            "## Task 3\n"
            "<!--metadata\n"
            "auto_approve: false\n"
            "-->\n"
            "Desc 3\n"
        )
        tickets = parse_tickets(md)
        assert len(tickets) == 3
        assert tickets[0].metadata["auto_approve"] is True
        assert tickets[1].metadata is None
        assert tickets[2].metadata["auto_approve"] is False

    def test_parse_metadata_with_status_tag(self):
        """Metadata should work with status tags."""
        md = (
            "## [in progress] Task title\n"
            "<!--metadata\n"
            "auto_approve: true\n"
            "-->\n"
            "Description\n"
        )
        tickets = parse_tickets(md)
        assert tickets[0].status == TicketStatus.IN_PROGRESS
        assert tickets[0].metadata["auto_approve"] is True

    def test_parse_empty_metadata_block(self):
        """Empty metadata block should result in empty dict or None."""
        md = (
            "## Task title\n"
            "<!--metadata\n"
            "-->\n"
            "Description\n"
        )
        tickets = parse_tickets(md)
        # Empty metadata block could be None or {}
        assert tickets[0].metadata is None or tickets[0].metadata == {}

    def test_parse_malformed_metadata_ignored(self):
        """Malformed metadata should be treated as regular content."""
        md = (
            "## Task title\n"
            "<!--metadata\n"
            "not valid yaml: [[[]\n"
            "-->\n"
            "Description\n"
        )
        tickets = parse_tickets(md)
        # Should either skip metadata or include malformed block in description
        # Implementation should gracefully handle this
        assert len(tickets) == 1

    def test_metadata_in_code_block_ignored(self):
        """Metadata-like content in code blocks should not be parsed."""
        md = (
            "## Task title\n"
            "Description\n"
            "```\n"
            "<!--metadata\n"
            "auto_approve: true\n"
            "-->\n"
            "```\n"
        )
        tickets = parse_tickets(md)
        assert tickets[0].metadata is None


# ---------------------------------------------------------------------------
# Writing metadata to markdown
# ---------------------------------------------------------------------------


class TestWriteTicketMetadata:
    """Test serializing metadata to DB."""

    def test_add_ticket_with_metadata(self, tmp_path: Path):
        """add_ticket should accept and serialize metadata."""
        t = add_ticket(
            tmp_path,
            "Task title",
            "Description",
            metadata={"auto_approve": True},
        )
        assert t.metadata == {"auto_approve": True}

        # Read back and verify
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert tickets[0].metadata["auto_approve"] is True

    def test_add_ticket_without_metadata(self, tmp_path: Path):
        """add_ticket without metadata should work normally."""
        t = add_ticket(tmp_path, "Task title", "Description")
        assert t.metadata is None

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is None

    def test_update_ticket_set_metadata(self, tmp_path: Path):
        """update_ticket should be able to set metadata."""
        add_ticket(tmp_path, "Original title", "Description")

        update_ticket(
            tmp_path,
            1,
            metadata={"auto_approve": True},
        )

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["auto_approve"] is True

    def test_update_ticket_change_metadata(self, tmp_path: Path):
        """update_ticket should be able to change existing metadata."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={"auto_approve": False},
        )

        update_ticket(
            tmp_path,
            1,
            metadata={"auto_approve": True},
        )

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["auto_approve"] is True

    def test_update_ticket_remove_metadata(self, tmp_path: Path):
        """update_ticket with metadata=None should remove metadata."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={"auto_approve": True},
        )

        update_ticket(tmp_path, 1, metadata=None)

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is None

    def test_update_ticket_preserves_metadata_when_not_specified(self, tmp_path: Path):
        """update_ticket should preserve metadata if not specified in update."""
        add_ticket(
            tmp_path,
            "Original title",
            "Description",
            metadata={"auto_approve": True},
        )

        update_ticket(tmp_path, 1, title="New title")

        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "New title"
        assert tickets[0].metadata["auto_approve"] is True

    def test_set_ticket_status_preserves_metadata(self, tmp_path: Path):
        """set_ticket_status should preserve metadata."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={"auto_approve": True},
        )

        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)

        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.IN_PROGRESS
        assert tickets[0].metadata["auto_approve"] is True

    def test_round_trip_metadata(self, tmp_path: Path):
        """Metadata should survive multiple read/write cycles."""
        add_ticket(
            tmp_path,
            "Task",
            "Desc",
            metadata={"auto_approve": True, "priority": "high"},
        )

        # Update status
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)

        # Update title
        update_ticket(tmp_path, 1, title="Updated task")

        # Read back
        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "Updated task"
        assert tickets[0].status == TicketStatus.IN_PROGRESS
        assert tickets[0].metadata["auto_approve"] is True
        assert tickets[0].metadata["priority"] == "high"

    def test_metadata_stored_in_db(self, tmp_path: Path):
        """Metadata should be stored in the DB."""
        add_ticket(
            tmp_path,
            "Task",
            "Description",
            metadata={"auto_approve": True},
        )

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is not None
        assert tickets[0].metadata["auto_approve"] is True

    def test_delete_ticket_with_metadata(self, tmp_path: Path):
        """delete_ticket should work with tickets that have metadata."""
        add_ticket(
            tmp_path,
            "Task 1",
            "Desc 1",
            metadata={"auto_approve": True},
        )
        add_ticket(tmp_path, "Task 2", "Desc 2")

        delete_ticket(tmp_path, 1)

        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert tickets[0].title == "Task 2"


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


class TestTicketMetadataBackwardCompatibility:
    """Test that tickets without metadata continue to work."""

    def test_tickets_without_metadata_work(self, tmp_path: Path):
        """Tickets created without metadata should work correctly."""
        add_ticket(tmp_path, "Old task 1", "Description")
        add_ticket(tmp_path, "Old task 2", "Another desc")
        set_ticket_status(tmp_path, 2, TicketStatus.DONE)

        tickets = read_tickets(tmp_path)
        assert len(tickets) == 2
        assert tickets[0].title == "Old task 1"
        assert tickets[0].metadata is None
        assert tickets[1].title == "Old task 2"
        assert tickets[1].status == TicketStatus.DONE
        assert tickets[1].metadata is None

    def test_mixed_metadata_and_no_metadata_tickets(self, tmp_path: Path):
        """Mix of tickets with and without metadata should work."""
        add_ticket(tmp_path, "Old style", "No metadata")
        add_ticket(
            tmp_path,
            "New style",
            "Has metadata",
            metadata={"auto_approve": True},
        )
        add_ticket(tmp_path, "Another old", "Also no metadata")

        tickets = read_tickets(tmp_path)
        assert len(tickets) == 3
        assert tickets[0].metadata is None
        assert tickets[1].metadata["auto_approve"] is True
        assert tickets[2].metadata is None

    def test_operations_on_tickets_without_metadata_work(self, tmp_path: Path):
        """All ticket operations should work on tickets without metadata."""
        add_ticket(tmp_path, "Old task", "Description")

        # Status change
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.IN_PROGRESS
        assert tickets[0].metadata is None

        # Update
        update_ticket(tmp_path, 1, title="Updated old task")
        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "Updated old task"
        assert tickets[0].metadata is None
