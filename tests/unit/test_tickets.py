"""Tests for the markdown-based ticketing system."""

from __future__ import annotations

from pathlib import Path

import pytest

from levelup.core.tickets import (
    Ticket,
    TicketStatus,
    get_next_ticket,
    get_tickets_path,
    parse_tickets,
    read_tickets,
    set_ticket_status,
    update_ticket,
)


# ---------------------------------------------------------------------------
# TestTicketModel
# ---------------------------------------------------------------------------


class TestTicketModel:
    def test_defaults(self):
        t = Ticket(number=1, title="Some task")
        assert t.status == TicketStatus.PENDING
        assert t.description == ""
        assert t.number == 1

    def test_to_task_input(self):
        t = Ticket(number=3, title="Fix bug", description="Details here")
        ti = t.to_task_input()
        assert ti.title == "Fix bug"
        assert ti.description == "Details here"
        assert ti.source == "ticket"
        assert ti.source_id == "ticket:3"


# ---------------------------------------------------------------------------
# TestParseTickets
# ---------------------------------------------------------------------------


class TestParseTickets:
    def test_empty_string(self):
        assert parse_tickets("") == []

    def test_single_pending(self):
        md = "## Add login\nImplement JWT.\n"
        tickets = parse_tickets(md)
        assert len(tickets) == 1
        assert tickets[0].title == "Add login"
        assert tickets[0].status == TicketStatus.PENDING
        assert "JWT" in tickets[0].description

    def test_all_statuses(self):
        md = (
            "## Pending task\n"
            "Desc A\n\n"
            "## [in progress] Active task\n"
            "Desc B\n\n"
            "## [done] Finished task\n"
            "Desc C\n\n"
            "## [merged] Merged task\n"
            "Desc D\n"
        )
        tickets = parse_tickets(md)
        assert len(tickets) == 4
        assert tickets[0].status == TicketStatus.PENDING
        assert tickets[1].status == TicketStatus.IN_PROGRESS
        assert tickets[2].status == TicketStatus.DONE
        assert tickets[3].status == TicketStatus.MERGED

    def test_numbering_is_positional(self):
        md = "## A\n\n## B\n\n## C\n"
        tickets = parse_tickets(md)
        assert [t.number for t in tickets] == [1, 2, 3]

    def test_case_insensitive_tags(self):
        md = "## [In Progress] Task\n\n## [DONE] Task2\n\n## [Merged] Task3\n"
        tickets = parse_tickets(md)
        assert tickets[0].status == TicketStatus.IN_PROGRESS
        assert tickets[1].status == TicketStatus.DONE
        assert tickets[2].status == TicketStatus.MERGED

    def test_h1_heading_ignored(self):
        md = "# Tickets\n\n## Real task\nBody\n"
        tickets = parse_tickets(md)
        assert len(tickets) == 1
        assert tickets[0].title == "Real task"

    def test_h3_not_a_ticket(self):
        md = "## Main task\n### Sub-heading\nDetails\n"
        tickets = parse_tickets(md)
        assert len(tickets) == 1
        assert "Sub-heading" in tickets[0].description

    def test_code_block_hides_headings(self):
        md = (
            "## Real ticket\n"
            "Before code\n"
            "```\n"
            "## Not a ticket\n"
            "```\n"
            "After code\n"
        )
        tickets = parse_tickets(md)
        assert len(tickets) == 1
        assert "Not a ticket" in tickets[0].description

    def test_empty_description(self):
        md = "## Task A\n## Task B\n"
        tickets = parse_tickets(md)
        assert tickets[0].description == ""
        assert tickets[1].description == ""

    def test_multiline_description(self):
        md = (
            "## Task\n"
            "Line 1\n"
            "Line 2\n"
            "- Bullet\n"
        )
        tickets = parse_tickets(md)
        assert "Line 1" in tickets[0].description
        assert "Line 2" in tickets[0].description
        assert "Bullet" in tickets[0].description

    def test_windows_line_endings(self):
        md = "## Task\r\nDescription\r\n"
        tickets = parse_tickets(md)
        assert len(tickets) == 1
        assert tickets[0].title == "Task"
        assert "Description" in tickets[0].description

    def test_whitespace_in_tag(self):
        md = "## [in progress]   Spaced title  \nBody\n"
        tickets = parse_tickets(md)
        assert tickets[0].title == "Spaced title"
        assert tickets[0].status == TicketStatus.IN_PROGRESS

    def test_description_stripped(self):
        md = "## Task\n\n  Body with leading blank  \n\n"
        tickets = parse_tickets(md)
        assert tickets[0].description == "Body with leading blank"

    def test_fenced_code_block_with_triple_backtick(self):
        md = (
            "## Setup CI\n"
            "Configure actions:\n"
            "```yaml\n"
            "name: CI\n"
            "## This is yaml, not a heading\n"
            "```\n"
        )
        tickets = parse_tickets(md)
        assert len(tickets) == 1
        assert "yaml" in tickets[0].description


# ---------------------------------------------------------------------------
# TestGetTicketsPath
# ---------------------------------------------------------------------------


class TestGetTicketsPath:
    def test_default_path(self, tmp_path: Path):
        assert get_tickets_path(tmp_path) == tmp_path / "levelup" / "tickets.md"

    def test_custom_filename(self, tmp_path: Path):
        assert get_tickets_path(tmp_path, "backlog.md") == tmp_path / "backlog.md"


# ---------------------------------------------------------------------------
# TestReadTickets
# ---------------------------------------------------------------------------


class TestReadTickets:
    def test_missing_file_returns_empty(self, tmp_path: Path):
        assert read_tickets(tmp_path) == []

    def test_reads_from_file(self, tmp_path: Path):
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## Task one\nDesc\n\n## [done] Task two\n",
            encoding="utf-8",
        )
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 2
        assert tickets[0].title == "Task one"
        assert tickets[1].status == TicketStatus.DONE

    def test_custom_filename(self, tmp_path: Path):
        (tmp_path / "backlog.md").write_text("## My task\n", encoding="utf-8")
        tickets = read_tickets(tmp_path, "backlog.md")
        assert len(tickets) == 1


# ---------------------------------------------------------------------------
# TestGetNextTicket
# ---------------------------------------------------------------------------


class TestGetNextTicket:
    def test_returns_first_pending(self, tmp_path: Path):
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## [done] Done task\n\n## Pending task\n\n## Another pending\n",
            encoding="utf-8",
        )
        t = get_next_ticket(tmp_path)
        assert t is not None
        assert t.title == "Pending task"
        assert t.number == 2

    def test_returns_none_when_all_done(self, tmp_path: Path):
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## [done] A\n\n## [merged] B\n",
            encoding="utf-8",
        )
        assert get_next_ticket(tmp_path) is None

    def test_returns_none_for_missing_file(self, tmp_path: Path):
        assert get_next_ticket(tmp_path) is None

    def test_skips_in_progress(self, tmp_path: Path):
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## [in progress] Active\n\n## Next one\n",
            encoding="utf-8",
        )
        t = get_next_ticket(tmp_path)
        assert t is not None
        assert t.title == "Next one"


# ---------------------------------------------------------------------------
# TestSetTicketStatus
# ---------------------------------------------------------------------------


class TestSetTicketStatus:
    def _write(self, tmp_path: Path, content: str) -> Path:
        d = tmp_path / "levelup"
        d.mkdir(exist_ok=True)
        p = d / "tickets.md"
        p.write_text(content, encoding="utf-8")
        return p

    def test_set_pending_to_in_progress(self, tmp_path: Path):
        self._write(tmp_path, "## My task\nDesc\n")
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.IN_PROGRESS

    def test_set_in_progress_to_done(self, tmp_path: Path):
        self._write(tmp_path, "## [in progress] My task\nDesc\n")
        set_ticket_status(tmp_path, 1, TicketStatus.DONE)
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DONE

    def test_set_done_to_merged(self, tmp_path: Path):
        self._write(tmp_path, "## [done] My task\nDesc\n")
        set_ticket_status(tmp_path, 1, TicketStatus.MERGED)
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.MERGED

    def test_set_back_to_pending(self, tmp_path: Path):
        self._write(tmp_path, "## [done] My task\nDesc\n")
        set_ticket_status(tmp_path, 1, TicketStatus.PENDING)
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.PENDING
        # Tag should be removed
        content = (tmp_path / "levelup" / "tickets.md").read_text()
        assert "[done]" not in content
        assert "[pending]" not in content

    def test_updates_correct_ticket(self, tmp_path: Path):
        self._write(
            tmp_path,
            "## First\n\n## Second\n\n## Third\n",
        )
        set_ticket_status(tmp_path, 2, TicketStatus.DONE)
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.PENDING
        assert tickets[1].status == TicketStatus.DONE
        assert tickets[2].status == TicketStatus.PENDING

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(IndexError):
            set_ticket_status(tmp_path, 1, TicketStatus.DONE)

    def test_invalid_number_raises(self, tmp_path: Path):
        self._write(tmp_path, "## Task\n")
        with pytest.raises(IndexError):
            set_ticket_status(tmp_path, 2, TicketStatus.DONE)

    def test_preserves_description(self, tmp_path: Path):
        self._write(
            tmp_path,
            "## My task\nImportant details\n- item 1\n- item 2\n",
        )
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)
        tickets = read_tickets(tmp_path)
        assert "Important details" in tickets[0].description

    def test_code_block_not_affected(self, tmp_path: Path):
        self._write(
            tmp_path,
            "## Task\n```\n## Fake heading\n```\n",
        )
        set_ticket_status(tmp_path, 1, TicketStatus.DONE)
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert tickets[0].status == TicketStatus.DONE

    def test_round_trip_preserves_content(self, tmp_path: Path):
        original = (
            "# Tickets\n\n"
            "## Add auth\n"
            "JWT-based login.\n\n"
            "## [in progress] Fix bug\n"
            "Connection pool issue.\n\n"
            "## [done] CI setup\n"
            "GitHub Actions.\n"
        )
        self._write(tmp_path, original)
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)
        set_ticket_status(tmp_path, 1, TicketStatus.PENDING)
        # After round-trip, content should still have all tickets
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 3
        assert tickets[0].title == "Add auth"
        assert tickets[1].title == "Fix bug"
        assert tickets[2].title == "CI setup"


# ---------------------------------------------------------------------------
# TestUpdateTicket
# ---------------------------------------------------------------------------


class TestUpdateTicket:
    def _write(self, tmp_path: Path, content: str) -> Path:
        d = tmp_path / "levelup"
        d.mkdir(exist_ok=True)
        p = d / "tickets.md"
        p.write_text(content, encoding="utf-8")
        return p

    def test_update_title_only(self, tmp_path: Path):
        self._write(tmp_path, "## Old title\nDescription\n")
        update_ticket(tmp_path, 1, title="New title")
        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "New title"
        assert "Description" in tickets[0].description

    def test_update_description_only(self, tmp_path: Path):
        self._write(tmp_path, "## My task\nOld desc\n")
        update_ticket(tmp_path, 1, description="New desc\nLine 2")
        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "My task"
        assert "New desc" in tickets[0].description
        assert "Line 2" in tickets[0].description
        assert "Old desc" not in tickets[0].description

    def test_update_both(self, tmp_path: Path):
        self._write(tmp_path, "## Old title\nOld desc\n")
        update_ticket(tmp_path, 1, title="New title", description="New desc")
        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "New title"
        assert "New desc" in tickets[0].description
        assert "Old desc" not in tickets[0].description

    def test_preserves_status_tag(self, tmp_path: Path):
        self._write(tmp_path, "## [in progress] Active task\nDesc\n")
        update_ticket(tmp_path, 1, title="Renamed task")
        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "Renamed task"
        assert tickets[0].status == TicketStatus.IN_PROGRESS

    def test_correct_ticket_in_multi_file(self, tmp_path: Path):
        self._write(
            tmp_path,
            "## First\nDesc A\n\n## Second\nDesc B\n\n## Third\nDesc C\n",
        )
        update_ticket(tmp_path, 2, title="Updated Second", description="New B")
        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "First"
        assert "Desc A" in tickets[0].description
        assert tickets[1].title == "Updated Second"
        assert "New B" in tickets[1].description
        assert tickets[2].title == "Third"
        assert "Desc C" in tickets[2].description

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(IndexError, match="not found"):
            update_ticket(tmp_path, 1, title="X")

    def test_invalid_number_raises(self, tmp_path: Path):
        self._write(tmp_path, "## Task\n")
        with pytest.raises(IndexError, match="not found"):
            update_ticket(tmp_path, 5, title="X")

    def test_preserves_other_tickets(self, tmp_path: Path):
        self._write(
            tmp_path,
            "## [done] Alpha\nA desc\n\n## Beta\nB desc\n\n## [merged] Gamma\nG desc\n",
        )
        update_ticket(tmp_path, 2, title="Beta v2")
        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "Alpha"
        assert tickets[0].status == TicketStatus.DONE
        assert tickets[1].title == "Beta v2"
        assert tickets[2].title == "Gamma"
        assert tickets[2].status == TicketStatus.MERGED

    def test_handles_code_blocks_in_description(self, tmp_path: Path):
        self._write(
            tmp_path,
            "## Task\n```\n## Not a heading\n```\nAfter code\n",
        )
        update_ticket(tmp_path, 1, description="Replaced\n```\ncode\n```\n")
        tickets = read_tickets(tmp_path)
        assert "Replaced" in tickets[0].description
        assert "code" in tickets[0].description

    def test_empty_description_clears_body(self, tmp_path: Path):
        self._write(tmp_path, "## Task\nOld body\nMore lines\n")
        update_ticket(tmp_path, 1, description="")
        tickets = read_tickets(tmp_path)
        assert tickets[0].description == ""
