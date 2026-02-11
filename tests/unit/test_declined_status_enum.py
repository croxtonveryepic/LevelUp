"""Unit tests for DECLINED status in TicketStatus enum and markdown parsing."""

from __future__ import annotations

from pathlib import Path

from levelup.core.tickets import (
    TicketStatus,
    parse_tickets,
    read_tickets,
    set_ticket_status,
    add_ticket,
)


class TestDeclinedStatusEnum:
    """Test the DECLINED status value in the TicketStatus enum."""

    def test_declined_status_exists(self):
        """DECLINED status should exist in TicketStatus enum."""
        assert hasattr(TicketStatus, "DECLINED")

    def test_declined_status_value(self):
        """DECLINED status should have value 'declined'."""
        assert TicketStatus.DECLINED == "declined"
        assert TicketStatus.DECLINED.value == "declined"

    def test_all_ticket_statuses(self):
        """TicketStatus enum should have all expected statuses."""
        expected = {"PENDING", "IN_PROGRESS", "DONE", "MERGED", "DECLINED"}
        actual = {s.name for s in TicketStatus}
        assert actual == expected

    def test_declined_is_string_enum(self):
        """DECLINED status should be a string enum value."""
        assert isinstance(TicketStatus.DECLINED, str)
        assert isinstance(TicketStatus.DECLINED.value, str)


class TestDeclinedStatusMarkdownParsing:
    """Test parsing [declined] status tag from markdown."""

    def test_parse_declined_status_tag(self):
        """Parser should recognize [declined] tag in ticket headings."""
        text = "## [declined] Task Title\nDescription here"
        tickets = parse_tickets(text)
        assert len(tickets) == 1
        assert tickets[0].status == TicketStatus.DECLINED
        assert tickets[0].title == "Task Title"

    def test_parse_declined_case_insensitive(self):
        """Parser should recognize [DECLINED] and [Declined] tags."""
        text = "## [DECLINED] Upper Case\n\n## [Declined] Mixed Case"
        tickets = parse_tickets(text)
        assert len(tickets) == 2
        assert tickets[0].status == TicketStatus.DECLINED
        assert tickets[1].status == TicketStatus.DECLINED

    def test_parse_declined_with_extra_spaces(self):
        """Parser should handle extra spaces in [declined] tag."""
        text = "## [declined]   Task with spaces\nDescription"
        tickets = parse_tickets(text)
        assert len(tickets) == 1
        assert tickets[0].status == TicketStatus.DECLINED
        assert tickets[0].title == "Task with spaces"

    def test_parse_multiple_statuses_including_declined(self):
        """Parser should handle multiple tickets with various statuses."""
        text = """## Pending Task

## [in progress] Working Task

## [done] Completed Task

## [declined] Declined Task

## [merged] Merged Task
"""
        tickets = parse_tickets(text)
        assert len(tickets) == 5
        assert tickets[0].status == TicketStatus.PENDING
        assert tickets[1].status == TicketStatus.IN_PROGRESS
        assert tickets[2].status == TicketStatus.DONE
        assert tickets[3].status == TicketStatus.DECLINED
        assert tickets[4].status == TicketStatus.MERGED

    def test_declined_tag_preserved_in_title(self):
        """Parser should not include [declined] tag in ticket title."""
        text = "## [declined] My Declined Ticket\nSome description"
        tickets = parse_tickets(text)
        assert tickets[0].title == "My Declined Ticket"
        assert "[declined]" not in tickets[0].title


class TestDeclinedStatusPersistence:
    """Test reading and writing declined status to/from files."""

    def test_read_declined_ticket_from_file(self, tmp_path: Path):
        """read_tickets() should correctly parse declined tickets from file."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## [declined] Rejected Feature\nNot needed anymore",
            encoding="utf-8"
        )

        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert tickets[0].status == TicketStatus.DECLINED
        assert tickets[0].title == "Rejected Feature"

    def test_set_ticket_status_to_declined(self, tmp_path: Path):
        """set_ticket_status() should be able to change status to DECLINED."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "My Task", "Description")

        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DECLINED

        # Verify markdown file contains [declined] tag
        content = (tickets_dir / "tickets.md").read_text(encoding="utf-8")
        assert "[declined]" in content.lower()

    def test_set_declined_preserves_title(self, tmp_path: Path):
        """Setting status to declined should preserve ticket title."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Original Title", "Description")

        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "Original Title"

    def test_set_declined_preserves_description(self, tmp_path: Path):
        """Setting status to declined should preserve ticket description."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Important details here")

        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        tickets = read_tickets(tmp_path)
        assert tickets[0].description == "Important details here"

    def test_set_declined_preserves_metadata(self, tmp_path: Path):
        """Setting status to declined should preserve ticket metadata."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Desc", metadata={"priority": "high"})

        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is not None
        assert tickets[0].metadata.get("priority") == "high"

    def test_change_from_declined_to_other_status(self, tmp_path: Path):
        """Should be able to change status from declined to other statuses."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")

        # Set to declined
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)
        assert read_tickets(tmp_path)[0].status == TicketStatus.DECLINED

        # Change to in progress
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)
        assert read_tickets(tmp_path)[0].status == TicketStatus.IN_PROGRESS

    def test_declined_tag_format_in_file(self, tmp_path: Path):
        """Declined tag should be written in correct markdown format."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "My Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        content = (tickets_dir / "tickets.md").read_text(encoding="utf-8")
        # Should have format: ## [declined] Title
        assert "## [declined] My Task" in content


class TestDeclinedStatusEdgeCases:
    """Test edge cases for declined status handling."""

    def test_declined_with_code_block_in_description(self, tmp_path: Path):
        """Declined status should work with code blocks in description."""
        text = """## [declined] Task with Code

```python
def example():
    pass
```
"""
        tickets = parse_tickets(text)
        assert len(tickets) == 1
        assert tickets[0].status == TicketStatus.DECLINED
        assert "```python" in tickets[0].description

    def test_declined_with_metadata_block(self, tmp_path: Path):
        """Declined status should work with metadata blocks."""
        text = """## [declined] Task with Metadata
<!--metadata
priority: high
-->
Description here
"""
        tickets = parse_tickets(text)
        assert len(tickets) == 1
        assert tickets[0].status == TicketStatus.DECLINED
        assert tickets[0].metadata is not None
        assert tickets[0].metadata.get("priority") == "high"

    def test_declined_with_unicode_title(self):
        """Declined status should work with unicode characters in title."""
        text = "## [declined] 日本語 Task ✨\nDescription"
        tickets = parse_tickets(text)
        assert tickets[0].status == TicketStatus.DECLINED
        assert tickets[0].title == "日本語 Task ✨"

    def test_declined_status_in_regex_pattern(self):
        """_STATUS_PATTERN regex should include declined."""
        from levelup.core.tickets import _STATUS_PATTERN

        # Test that regex matches [declined]
        match = _STATUS_PATTERN.match("[declined] Test Title")
        assert match is not None
        assert match.group(1).lower() == "declined"

        # Test case insensitivity
        match = _STATUS_PATTERN.match("[DECLINED] Test Title")
        assert match is not None
        assert match.group(1).lower() == "declined"
