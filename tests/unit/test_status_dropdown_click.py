"""Test updating ticket status by clicking the status dropdown."""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from levelup.core.tickets import TicketStatus, add_ticket, read_tickets


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _make_widget(tmp_path):
    from levelup.gui.ticket_detail import TicketDetailWidget

    (tmp_path / "levelup").mkdir(exist_ok=True)
    return TicketDetailWidget(project_path=str(tmp_path))


def _select_status(dropdown, target_status_text: str) -> None:
    """Simulate a user clicking the dropdown and picking an option."""
    for i in range(dropdown.count()):
        if target_status_text in dropdown.itemText(i).lower():
            # showPopup + setCurrentIndex mirrors a real click selection
            dropdown.showPopup()
            dropdown.setCurrentIndex(i)
            dropdown.hidePopup()
            return
    raise ValueError(f"Status '{target_status_text}' not found in dropdown")


class TestClickDropdownUpdatesStatus:
    """Simulate clicking the dropdown to change a ticket's status and saving."""

    def test_click_pending_to_done(self, qapp, tmp_path):
        widget = _make_widget(tmp_path)
        ticket = add_ticket(tmp_path, "Fix login bug", "Users cannot log in")
        widget.set_ticket(ticket)

        _select_status(widget.status_dropdown, "done")
        assert widget.is_dirty

        widget.save_ticket()

        persisted = read_tickets(tmp_path)[0]
        assert persisted.status == TicketStatus.DONE

    def test_click_pending_to_in_progress(self, qapp, tmp_path):
        widget = _make_widget(tmp_path)
        ticket = add_ticket(tmp_path, "Add caching", "Speed up API calls")
        widget.set_ticket(ticket)

        _select_status(widget.status_dropdown, "progress")
        widget.save_ticket()

        assert read_tickets(tmp_path)[0].status == TicketStatus.IN_PROGRESS

    def test_click_done_to_merged(self, qapp, tmp_path):
        from levelup.core.tickets import set_ticket_status

        widget = _make_widget(tmp_path)
        add_ticket(tmp_path, "Refactor auth", "Clean up module")
        set_ticket_status(tmp_path, 1, TicketStatus.DONE)

        ticket = read_tickets(tmp_path)[0]
        widget.set_ticket(ticket)

        _select_status(widget.status_dropdown, "merged")
        widget.save_ticket()

        assert read_tickets(tmp_path)[0].status == TicketStatus.MERGED

    def test_click_in_progress_to_declined(self, qapp, tmp_path):
        from levelup.core.tickets import set_ticket_status

        widget = _make_widget(tmp_path)
        add_ticket(tmp_path, "Dark mode", "User requested")
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)

        ticket = read_tickets(tmp_path)[0]
        widget.set_ticket(ticket)

        _select_status(widget.status_dropdown, "declined")
        widget.save_ticket()

        assert read_tickets(tmp_path)[0].status == TicketStatus.DECLINED

    def test_click_declined_back_to_pending(self, qapp, tmp_path):
        from levelup.core.tickets import set_ticket_status

        widget = _make_widget(tmp_path)
        add_ticket(tmp_path, "Revisited feature", "Re-evaluate")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        ticket = read_tickets(tmp_path)[0]
        widget.set_ticket(ticket)

        _select_status(widget.status_dropdown, "pending")
        widget.save_ticket()

        assert read_tickets(tmp_path)[0].status == TicketStatus.PENDING

    def test_dropdown_reflects_new_status_after_reload(self, qapp, tmp_path):
        """After save and reload, dropdown should show the updated status."""
        widget = _make_widget(tmp_path)
        ticket = add_ticket(tmp_path, "Persist check", "Verify round-trip")
        widget.set_ticket(ticket)

        _select_status(widget.status_dropdown, "done")
        widget.save_ticket()

        # Reload from disk
        reloaded = read_tickets(tmp_path)[0]
        widget.set_ticket(reloaded)

        assert "done" in widget.status_dropdown.currentText().lower()

    def test_title_and_description_preserved_after_status_click(self, qapp, tmp_path):
        widget = _make_widget(tmp_path)
        ticket = add_ticket(tmp_path, "Important Task", "Do not lose this description")
        widget.set_ticket(ticket)

        _select_status(widget.status_dropdown, "done")
        widget.save_ticket()

        persisted = read_tickets(tmp_path)[0]
        assert persisted.title == "Important Task"
        assert persisted.description == "Do not lose this description"
        assert persisted.status == TicketStatus.DONE
