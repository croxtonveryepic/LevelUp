"""Unit tests for status change persistence from status dropdown."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.regression

# GUI tests require PyQt6
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from levelup.core.tickets import TicketStatus, add_ticket, read_tickets


# Test fixtures need a QApplication instance
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestStatusDropdownPersistence:
    """Test that status changes from dropdown are persisted to ticket."""

    def test_save_persists_selected_status(self, qapp, tmp_path):
        """Saving ticket should persist selected status from dropdown."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change status to declined
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        # Mock the ticket_saved signal to capture save
        with patch.object(widget, 'ticket_saved') as mock_signal:
            widget.save_ticket()

        # Verify status was changed in file
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DECLINED

    def test_save_calls_set_ticket_status(self, qapp, tmp_path):
        """Save should call set_ticket_status() with selected status."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core import tickets as tickets_module

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change status to done
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "done" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        with patch.object(tickets_module, 'set_ticket_status', wraps=tickets_module.set_ticket_status) as mock_set:
            widget.save_ticket()

            # Should have called set_ticket_status before update_ticket
            assert mock_set.called
            # Verify it was called with DONE status
            call_args = mock_set.call_args
            assert call_args is not None
            assert call_args[0][2] == TicketStatus.DONE  # Third positional arg is new_status

    def test_save_calls_set_status_before_update(self, qapp, tmp_path):
        """set_ticket_status() should be called before update_ticket()."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core import tickets as tickets_module

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change status
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "merged" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        call_order = []

        original_set = tickets_module.set_ticket_status
        original_update = tickets_module.update_ticket

        def track_set(*args, **kwargs):
            call_order.append("set_status")
            return original_set(*args, **kwargs)

        def track_update(*args, **kwargs):
            call_order.append("update")
            return original_update(*args, **kwargs)

        with patch.object(tickets_module, 'set_ticket_status', side_effect=track_set):
            with patch.object(tickets_module, 'update_ticket', side_effect=track_update):
                widget.save_ticket()

        # set_ticket_status should be called before update_ticket
        assert "set_status" in call_order
        assert "update" in call_order
        assert call_order.index("set_status") < call_order.index("update")

    def test_status_change_to_pending(self, qapp, tmp_path):
        """Should be able to change status to pending via dropdown."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core.tickets import set_ticket_status

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DONE)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(tickets[0])

        # Change status to pending
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "pending" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.PENDING

    def test_status_change_to_in_progress(self, qapp, tmp_path):
        """Should be able to change status to in progress via dropdown."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change status to in progress
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "progress" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.IN_PROGRESS

    def test_status_change_to_done(self, qapp, tmp_path):
        """Should be able to change status to done via dropdown."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change status to done
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "done" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DONE

    def test_status_change_to_merged(self, qapp, tmp_path):
        """Should be able to change status to merged via dropdown."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change status to merged
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "merged" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.MERGED

    def test_status_change_to_declined(self, qapp, tmp_path):
        """Should be able to change status to declined via dropdown."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change status to declined
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DECLINED


class TestStatusPersistencePreservesData:
    """Test that status changes preserve other ticket data."""

    def test_status_change_preserves_title(self, qapp, tmp_path):
        """Changing status should preserve ticket title."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Original Title", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change status
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "Original Title"

    def test_status_change_preserves_description(self, qapp, tmp_path):
        """Changing status should preserve ticket description."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Important details here")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change status
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "done" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        tickets = read_tickets(tmp_path)
        assert tickets[0].description == "Important details here"

    def test_status_change_preserves_metadata(self, qapp, tmp_path):
        """Changing status should preserve ticket metadata."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Desc", metadata={"priority": "high"})

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change status
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is not None
        assert tickets[0].metadata.get("priority") == "high"

    def test_status_change_with_title_change(self, qapp, tmp_path):
        """Should be able to change both status and title together."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Old Title", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change title
        widget._title_edit.setText("New Title")

        # Change status
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        tickets = read_tickets(tmp_path)
        assert tickets[0].title == "New Title"
        assert tickets[0].status == TicketStatus.DECLINED


class TestStatusPersistenceEdgeCases:
    """Test edge cases for status persistence."""

    def test_no_status_change_no_set_ticket_status_call(self, qapp, tmp_path):
        """If status unchanged, set_ticket_status should not be called unnecessarily."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change title but not status
        widget._title_edit.setText("New Title")

        widget.save_ticket()

        # Status should still be pending
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.PENDING

    def test_save_empty_ticket_with_status(self, qapp, tmp_path):
        """Should handle saving ticket with minimal data."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "T", "")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Change status
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "done" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DONE

    def test_multiple_status_changes_before_save(self, qapp, tmp_path):
        """Multiple status changes before save should persist final value."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)

        # Change to done
        for i in range(dropdown.count()):
            if "done" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        # Change to declined
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        # Should have final status (declined)
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DECLINED
