"""Tests for the DB-backed ticketing system and markdown parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from levelup.core.tickets import (
    Ticket,
    TicketStatus,
    add_ticket,
    delete_ticket,
    get_next_ticket,
    get_ticket,
    get_tickets_path,
    parse_tickets,
    read_tickets,
    set_ticket_status,
    update_ticket,
)
from levelup.state.db import init_db


@pytest.fixture
def ticket_db(tmp_path: Path):
    """Create a temporary SQLite DB for ticket tests."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return db_path


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
# TestParseTickets (pure function, unchanged)
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
# TestGetTicketsPath (preserved, still useful for migration)
# ---------------------------------------------------------------------------


class TestGetTicketsPath:
    def test_default_path(self, tmp_path: Path):
        assert get_tickets_path(tmp_path) == tmp_path / "levelup" / "tickets.md"

    def test_custom_filename(self, tmp_path: Path):
        assert get_tickets_path(tmp_path, "backlog.md") == tmp_path / "backlog.md"


# ---------------------------------------------------------------------------
# TestReadTickets (DB-backed)
# ---------------------------------------------------------------------------


class TestReadTickets:
    def test_empty_db_returns_empty(self, tmp_path: Path, ticket_db: Path):
        assert read_tickets(tmp_path, db_path=ticket_db) == []

    def test_reads_from_db(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "Task one", "Desc", db_path=ticket_db)
        t2 = add_ticket(tmp_path, "Task two", "", db_path=ticket_db)
        set_ticket_status(tmp_path, t2.number, TicketStatus.DONE, db_path=ticket_db)

        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert len(tickets) == 2
        assert tickets[0].title == "Task one"
        assert tickets[1].status == TicketStatus.DONE


# ---------------------------------------------------------------------------
# TestGetNextTicket (DB-backed)
# ---------------------------------------------------------------------------


class TestGetNextTicket:
    def test_returns_first_pending(self, tmp_path: Path, ticket_db: Path):
        t1 = add_ticket(tmp_path, "Done task", db_path=ticket_db)
        set_ticket_status(tmp_path, t1.number, TicketStatus.DONE, db_path=ticket_db)
        add_ticket(tmp_path, "Pending task", db_path=ticket_db)
        add_ticket(tmp_path, "Another pending", db_path=ticket_db)

        t = get_next_ticket(tmp_path, db_path=ticket_db)
        assert t is not None
        assert t.title == "Pending task"
        assert t.number == 2

    def test_returns_none_when_all_done(self, tmp_path: Path, ticket_db: Path):
        t1 = add_ticket(tmp_path, "A", db_path=ticket_db)
        t2 = add_ticket(tmp_path, "B", db_path=ticket_db)
        set_ticket_status(tmp_path, t1.number, TicketStatus.DONE, db_path=ticket_db)
        set_ticket_status(tmp_path, t2.number, TicketStatus.MERGED, db_path=ticket_db)
        assert get_next_ticket(tmp_path, db_path=ticket_db) is None

    def test_returns_none_for_empty_db(self, tmp_path: Path, ticket_db: Path):
        assert get_next_ticket(tmp_path, db_path=ticket_db) is None

    def test_skips_in_progress(self, tmp_path: Path, ticket_db: Path):
        t1 = add_ticket(tmp_path, "Active", db_path=ticket_db)
        set_ticket_status(tmp_path, t1.number, TicketStatus.IN_PROGRESS, db_path=ticket_db)
        add_ticket(tmp_path, "Next one", db_path=ticket_db)

        t = get_next_ticket(tmp_path, db_path=ticket_db)
        assert t is not None
        assert t.title == "Next one"


# ---------------------------------------------------------------------------
# TestGetTicket (new, DB-backed)
# ---------------------------------------------------------------------------


class TestGetTicket:
    def test_found(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "First", db_path=ticket_db)
        add_ticket(tmp_path, "Second", db_path=ticket_db)
        t = get_ticket(tmp_path, 2, db_path=ticket_db)
        assert t is not None
        assert t.title == "Second"

    def test_not_found(self, tmp_path: Path, ticket_db: Path):
        assert get_ticket(tmp_path, 99, db_path=ticket_db) is None


# ---------------------------------------------------------------------------
# TestSetTicketStatus (DB-backed)
# ---------------------------------------------------------------------------


class TestSetTicketStatus:
    def test_set_pending_to_in_progress(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "My task", "Desc", db_path=ticket_db)
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS, db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].status == TicketStatus.IN_PROGRESS

    def test_set_in_progress_to_done(self, tmp_path: Path, ticket_db: Path):
        t = add_ticket(tmp_path, "My task", "Desc", db_path=ticket_db)
        set_ticket_status(tmp_path, t.number, TicketStatus.IN_PROGRESS, db_path=ticket_db)
        set_ticket_status(tmp_path, t.number, TicketStatus.DONE, db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].status == TicketStatus.DONE

    def test_set_done_to_merged(self, tmp_path: Path, ticket_db: Path):
        t = add_ticket(tmp_path, "My task", "Desc", db_path=ticket_db)
        set_ticket_status(tmp_path, t.number, TicketStatus.DONE, db_path=ticket_db)
        set_ticket_status(tmp_path, t.number, TicketStatus.MERGED, db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].status == TicketStatus.MERGED

    def test_set_back_to_pending(self, tmp_path: Path, ticket_db: Path):
        t = add_ticket(tmp_path, "My task", "Desc", db_path=ticket_db)
        set_ticket_status(tmp_path, t.number, TicketStatus.DONE, db_path=ticket_db)
        set_ticket_status(tmp_path, t.number, TicketStatus.PENDING, db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].status == TicketStatus.PENDING

    def test_updates_correct_ticket(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "First", db_path=ticket_db)
        add_ticket(tmp_path, "Second", db_path=ticket_db)
        add_ticket(tmp_path, "Third", db_path=ticket_db)
        set_ticket_status(tmp_path, 2, TicketStatus.DONE, db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].status == TicketStatus.PENDING
        assert tickets[1].status == TicketStatus.DONE
        assert tickets[2].status == TicketStatus.PENDING

    def test_not_found_raises(self, tmp_path: Path, ticket_db: Path):
        with pytest.raises(IndexError):
            set_ticket_status(tmp_path, 1, TicketStatus.DONE, db_path=ticket_db)

    def test_invalid_number_raises(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "Task", db_path=ticket_db)
        with pytest.raises(IndexError):
            set_ticket_status(tmp_path, 2, TicketStatus.DONE, db_path=ticket_db)

    def test_preserves_description(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "My task", "Important details\n- item 1\n- item 2", db_path=ticket_db)
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS, db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert "Important details" in tickets[0].description

    def test_round_trip_preserves_content(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "Add auth", "JWT-based login.", db_path=ticket_db)
        t2 = add_ticket(tmp_path, "Fix bug", "Connection pool issue.", db_path=ticket_db)
        set_ticket_status(tmp_path, t2.number, TicketStatus.IN_PROGRESS, db_path=ticket_db)
        t3 = add_ticket(tmp_path, "CI setup", "GitHub Actions.", db_path=ticket_db)
        set_ticket_status(tmp_path, t3.number, TicketStatus.DONE, db_path=ticket_db)

        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS, db_path=ticket_db)
        set_ticket_status(tmp_path, 1, TicketStatus.PENDING, db_path=ticket_db)

        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert len(tickets) == 3
        assert tickets[0].title == "Add auth"
        assert tickets[1].title == "Fix bug"
        assert tickets[2].title == "CI setup"


# ---------------------------------------------------------------------------
# TestUpdateTicket (DB-backed)
# ---------------------------------------------------------------------------


class TestUpdateTicket:
    def test_update_title_only(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "Old title", "Description", db_path=ticket_db)
        update_ticket(tmp_path, 1, title="New title", db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].title == "New title"
        assert "Description" in tickets[0].description

    def test_update_description_only(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "My task", "Old desc", db_path=ticket_db)
        update_ticket(tmp_path, 1, description="New desc\nLine 2", db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].title == "My task"
        assert "New desc" in tickets[0].description
        assert "Line 2" in tickets[0].description

    def test_update_both(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "Old title", "Old desc", db_path=ticket_db)
        update_ticket(tmp_path, 1, title="New title", description="New desc", db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].title == "New title"
        assert "New desc" in tickets[0].description

    def test_preserves_status(self, tmp_path: Path, ticket_db: Path):
        t = add_ticket(tmp_path, "Active task", "Desc", db_path=ticket_db)
        set_ticket_status(tmp_path, t.number, TicketStatus.IN_PROGRESS, db_path=ticket_db)
        update_ticket(tmp_path, t.number, title="Renamed task", db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].title == "Renamed task"
        assert tickets[0].status == TicketStatus.IN_PROGRESS

    def test_correct_ticket_in_multi(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "First", "Desc A", db_path=ticket_db)
        add_ticket(tmp_path, "Second", "Desc B", db_path=ticket_db)
        add_ticket(tmp_path, "Third", "Desc C", db_path=ticket_db)
        update_ticket(tmp_path, 2, title="Updated Second", description="New B", db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].title == "First"
        assert "Desc A" in tickets[0].description
        assert tickets[1].title == "Updated Second"
        assert "New B" in tickets[1].description
        assert tickets[2].title == "Third"
        assert "Desc C" in tickets[2].description

    def test_not_found_raises(self, tmp_path: Path, ticket_db: Path):
        with pytest.raises(IndexError):
            update_ticket(tmp_path, 1, title="X", db_path=ticket_db)

    def test_invalid_number_raises(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "Task", db_path=ticket_db)
        with pytest.raises(IndexError):
            update_ticket(tmp_path, 5, title="X", db_path=ticket_db)

    def test_preserves_other_tickets(self, tmp_path: Path, ticket_db: Path):
        t1 = add_ticket(tmp_path, "Alpha", "A desc", db_path=ticket_db)
        set_ticket_status(tmp_path, t1.number, TicketStatus.DONE, db_path=ticket_db)
        add_ticket(tmp_path, "Beta", "B desc", db_path=ticket_db)
        t3 = add_ticket(tmp_path, "Gamma", "G desc", db_path=ticket_db)
        set_ticket_status(tmp_path, t3.number, TicketStatus.MERGED, db_path=ticket_db)

        update_ticket(tmp_path, 2, title="Beta v2", db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].title == "Alpha"
        assert tickets[0].status == TicketStatus.DONE
        assert tickets[1].title == "Beta v2"
        assert tickets[2].title == "Gamma"
        assert tickets[2].status == TicketStatus.MERGED

    def test_empty_description_clears_body(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "Task", "Old body\nMore lines", db_path=ticket_db)
        update_ticket(tmp_path, 1, description="", db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].description == ""


# ---------------------------------------------------------------------------
# TestAddTicket (DB-backed)
# ---------------------------------------------------------------------------


class TestAddTicket:
    def test_creates_ticket(self, tmp_path: Path, ticket_db: Path):
        t = add_ticket(tmp_path, "First ticket", "Some description", db_path=ticket_db)
        assert t.number == 1
        assert t.title == "First ticket"
        assert t.description == "Some description"
        assert t.status == TicketStatus.PENDING

    def test_appends_to_existing(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "Existing task", "Desc", db_path=ticket_db)
        t = add_ticket(tmp_path, "Second task", "More info", db_path=ticket_db)
        assert t.number == 2
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert len(tickets) == 2
        assert tickets[0].title == "Existing task"
        assert tickets[1].title == "Second task"
        assert tickets[1].description == "More info"

    def test_empty_description(self, tmp_path: Path, ticket_db: Path):
        t = add_ticket(tmp_path, "No desc", db_path=ticket_db)
        assert t.description == ""
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets[0].description == ""

    def test_multiple_sequential_adds(self, tmp_path: Path, ticket_db: Path):
        t1 = add_ticket(tmp_path, "First", db_path=ticket_db)
        t2 = add_ticket(tmp_path, "Second", db_path=ticket_db)
        t3 = add_ticket(tmp_path, "Third", db_path=ticket_db)
        assert t1.number == 1
        assert t2.number == 2
        assert t3.number == 3
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert len(tickets) == 3
        assert [t.title for t in tickets] == ["First", "Second", "Third"]

    def test_round_trip(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "Round trip", "Detailed description\n- item 1\n- item 2", db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert len(tickets) == 1
        assert tickets[0].title == "Round trip"
        assert "item 1" in tickets[0].description
        assert "item 2" in tickets[0].description


# ---------------------------------------------------------------------------
# TestDeleteTicket (DB-backed)
# ---------------------------------------------------------------------------


class TestDeleteTicket:
    def test_delete_only_ticket(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "Only task", "Some desc", db_path=ticket_db)
        title = delete_ticket(tmp_path, 1, db_path=ticket_db)
        assert title == "Only task"
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert tickets == []

    def test_delete_first_of_multiple(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "First", "A", db_path=ticket_db)
        add_ticket(tmp_path, "Second", "B", db_path=ticket_db)
        add_ticket(tmp_path, "Third", "C", db_path=ticket_db)
        title = delete_ticket(tmp_path, 1, db_path=ticket_db)
        assert title == "First"
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert len(tickets) == 2
        # Stable numbering: ticket #2 and #3 keep their numbers
        assert tickets[0].title == "Second"
        assert tickets[0].number == 2
        assert tickets[1].title == "Third"
        assert tickets[1].number == 3

    def test_delete_middle(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "First", "A", db_path=ticket_db)
        add_ticket(tmp_path, "Second", "B", db_path=ticket_db)
        add_ticket(tmp_path, "Third", "C", db_path=ticket_db)
        title = delete_ticket(tmp_path, 2, db_path=ticket_db)
        assert title == "Second"
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert len(tickets) == 2
        assert tickets[0].title == "First"
        assert tickets[1].title == "Third"

    def test_delete_last(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "First", "A", db_path=ticket_db)
        add_ticket(tmp_path, "Second", "B", db_path=ticket_db)
        add_ticket(tmp_path, "Third", "C", db_path=ticket_db)
        title = delete_ticket(tmp_path, 3, db_path=ticket_db)
        assert title == "Third"
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert len(tickets) == 2
        assert tickets[0].title == "First"
        assert tickets[1].title == "Second"

    def test_delete_with_status_returns_bare_title(self, tmp_path: Path, ticket_db: Path):
        t = add_ticket(tmp_path, "Active task", "Desc", db_path=ticket_db)
        set_ticket_status(tmp_path, t.number, TicketStatus.IN_PROGRESS, db_path=ticket_db)
        title = delete_ticket(tmp_path, t.number, db_path=ticket_db)
        assert title == "Active task"

    def test_preserves_other_tickets_content_and_status(self, tmp_path: Path, ticket_db: Path):
        t1 = add_ticket(tmp_path, "Alpha", "A desc", db_path=ticket_db)
        set_ticket_status(tmp_path, t1.number, TicketStatus.DONE, db_path=ticket_db)
        add_ticket(tmp_path, "Beta", "B desc", db_path=ticket_db)
        t3 = add_ticket(tmp_path, "Gamma", "G desc", db_path=ticket_db)
        set_ticket_status(tmp_path, t3.number, TicketStatus.MERGED, db_path=ticket_db)

        delete_ticket(tmp_path, 2, db_path=ticket_db)
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert len(tickets) == 2
        assert tickets[0].title == "Alpha"
        assert tickets[0].status == TicketStatus.DONE
        assert "A desc" in tickets[0].description
        assert tickets[1].title == "Gamma"
        assert tickets[1].status == TicketStatus.MERGED
        assert "G desc" in tickets[1].description

    def test_not_found_raises(self, tmp_path: Path, ticket_db: Path):
        with pytest.raises(IndexError):
            delete_ticket(tmp_path, 1, db_path=ticket_db)

    def test_invalid_number_raises(self, tmp_path: Path, ticket_db: Path):
        add_ticket(tmp_path, "Task", db_path=ticket_db)
        with pytest.raises(IndexError):
            delete_ticket(tmp_path, 5, db_path=ticket_db)

    def test_stable_numbering_after_delete(self, tmp_path: Path, ticket_db: Path):
        """Deleting ticket #2 doesn't renumber #3."""
        add_ticket(tmp_path, "First", db_path=ticket_db)
        add_ticket(tmp_path, "Second", db_path=ticket_db)
        add_ticket(tmp_path, "Third", db_path=ticket_db)
        delete_ticket(tmp_path, 2, db_path=ticket_db)
        # New ticket gets #4, not #3
        t4 = add_ticket(tmp_path, "Fourth", db_path=ticket_db)
        assert t4.number == 4
        tickets = read_tickets(tmp_path, db_path=ticket_db)
        assert [t.number for t in tickets] == [1, 3, 4]
