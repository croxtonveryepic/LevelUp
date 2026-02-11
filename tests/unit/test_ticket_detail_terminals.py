"""Tests for per-ticket terminal instances in TicketDetailWidget."""

from __future__ import annotations

import pytest


def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def _make_ticket(number: int, title: str = "Test ticket"):
    from levelup.core.tickets import Ticket, TicketStatus
    return Ticket(number=number, title=title, status=TicketStatus.PENDING)


_qapp = None


def _ensure_qapp():
    global _qapp
    from PyQt6.QtWidgets import QApplication
    _qapp = QApplication.instance() or QApplication([])
    return _qapp


def _make_detail():
    _ensure_qapp()
    from levelup.gui.ticket_detail import TicketDetailWidget
    return TicketDetailWidget()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestPerTicketTerminals:
    """Verify that each ticket gets its own independent terminal instance."""

    def test_set_ticket_creates_terminal(self):
        detail = _make_detail()
        detail.set_ticket(_make_ticket(1))
        assert 1 in detail._terminals
        assert detail._current_terminal is detail._terminals[1]

    def test_different_tickets_get_different_terminals(self):
        detail = _make_detail()
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal

        detail.set_ticket(_make_ticket(2))
        term2 = detail._current_terminal

        assert term1 is not term2
        assert 1 in detail._terminals
        assert 2 in detail._terminals

    def test_same_ticket_reuses_terminal(self):
        detail = _make_detail()
        detail.set_ticket(_make_ticket(1))
        term_first = detail._current_terminal

        detail.set_ticket(_make_ticket(2))
        detail.set_ticket(_make_ticket(1))
        term_second = detail._current_terminal

        assert term_first is term_second

    def test_terminal_property_returns_current(self):
        detail = _make_detail()
        detail.set_ticket(_make_ticket(3))
        assert detail.terminal is detail._current_terminal
        assert detail.terminal is detail._terminals[3]

    def test_terminal_property_none_before_ticket(self):
        detail = _make_detail()
        assert detail.terminal is None

    def test_stacked_widget_shows_correct_terminal(self):
        detail = _make_detail()
        detail.set_ticket(_make_ticket(1))
        assert detail._terminal_stack.currentWidget() is detail._terminals[1]

        detail.set_ticket(_make_ticket(2))
        assert detail._terminal_stack.currentWidget() is detail._terminals[2]

    def test_project_context_propagated_to_new_terminals(self):
        detail = _make_detail()
        detail.set_project_context("/proj", "/db")

        detail.set_ticket(_make_ticket(1))
        term = detail._terminals[1]
        assert term._project_path == "/proj"
        assert term._db_path == "/db"

    def test_project_context_propagated_to_existing(self):
        detail = _make_detail()
        detail.set_ticket(_make_ticket(1))
        term = detail._terminals[1]

        detail.set_project_context("/proj", "/db")
        assert term._project_path == "/proj"
        assert term._db_path == "/db"

    def test_state_manager_propagated(self):
        from unittest.mock import MagicMock
        from levelup.state.manager import StateManager
        detail = _make_detail()
        fake_sm = MagicMock(spec=StateManager)
        fake_sm.get_run_for_ticket.return_value = None
        detail.set_project_context("/proj", "/db", state_manager=fake_sm)
        detail.set_ticket(_make_ticket(1))
        assert detail._terminals[1]._state_manager is fake_sm

    def test_remove_terminal_cleans_up(self):
        detail = _make_detail()
        detail.set_ticket(_make_ticket(1))
        detail.set_ticket(_make_ticket(2))
        assert detail._terminal_stack.count() == 2

        detail._remove_terminal(1)
        assert 1 not in detail._terminals
        assert detail._terminal_stack.count() == 1
        assert detail._current_terminal is detail._terminals[2]

    def test_remove_current_terminal_sets_none(self):
        detail = _make_detail()
        detail.set_ticket(_make_ticket(1))
        assert detail._current_terminal is not None

        detail._remove_terminal(1)
        assert detail._current_terminal is None

    def test_cleanup_all_terminals(self):
        detail = _make_detail()
        detail.set_ticket(_make_ticket(1))
        detail.set_ticket(_make_ticket(2))
        detail.set_ticket(_make_ticket(3))
        assert len(detail._terminals) == 3

        detail.cleanup_all_terminals()
        assert len(detail._terminals) == 0
        assert detail._current_terminal is None

    def test_create_mode_with_no_terminal(self):
        detail = _make_detail()
        detail.set_create_mode()
        assert detail._current_terminal is None

    def test_delete_removes_terminal(self):
        from unittest.mock import patch as _patch
        from PyQt6.QtWidgets import QMessageBox

        detail = _make_detail()
        detail.set_ticket(_make_ticket(5, title="Doomed"))
        assert 5 in detail._terminals

        deleted = []
        detail.ticket_deleted.connect(lambda n: deleted.append(n))

        with _patch(
            "levelup.gui.ticket_detail.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            detail._on_delete()

        assert deleted == [5]
        assert 5 not in detail._terminals

    def test_ticket_number_set_on_terminal(self):
        detail = _make_detail()
        detail.set_ticket(_make_ticket(7))
        assert detail._terminals[7]._ticket_number == 7
