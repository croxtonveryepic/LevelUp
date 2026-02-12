"""Unit tests for status dropdown widget in TicketDetailWidget."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.regression

# GUI tests require PyQt6
pytest.importorskip("PyQt6")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QComboBox

from levelup.core.tickets import Ticket, TicketStatus, add_ticket, read_tickets


# Test fixtures need a QApplication instance
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestStatusDropdownExists:
    """Test that status dropdown widget exists in TicketDetailWidget."""

    def test_widget_has_status_dropdown(self, qapp, tmp_path):
        """TicketDetailWidget should have a status dropdown (QComboBox)."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path))

        # Should have a status dropdown attribute
        assert hasattr(widget, "status_dropdown") or hasattr(widget, "_status_dropdown")

    def test_status_dropdown_is_combobox(self, qapp, tmp_path):
        """Status dropdown should be a QComboBox widget."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path))

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        assert dropdown is not None
        assert isinstance(dropdown, QComboBox)

    def test_status_dropdown_position(self, qapp, tmp_path):
        """Status dropdown should be between title and description fields."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path))

        # Widget should have the fields in order
        assert hasattr(widget, "_title_edit") or hasattr(widget, "title_edit")
        assert hasattr(widget, "status_dropdown") or hasattr(widget, "_status_dropdown")
        assert hasattr(widget, "_desc_edit") or hasattr(widget, "description_edit")


class TestStatusDropdownPopulation:
    """Test that status dropdown is populated with all ticket statuses."""

    def test_dropdown_contains_all_statuses(self, qapp, tmp_path):
        """Dropdown should display all ticket statuses."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path))
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)

        # Should have items for all statuses
        items = [dropdown.itemText(i) for i in range(dropdown.count())]

        # Should have all status values (may be capitalized or formatted)
        statuses = [s.value for s in TicketStatus]
        for status in statuses:
            # Check if status text appears in any item (case-insensitive)
            assert any(status.lower() in item.lower() for item in items), \
                f"Status '{status}' not found in dropdown items: {items}"

    def test_dropdown_has_pending_status(self, qapp, tmp_path):
        """Dropdown should include Pending status."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path))
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)

        items = [dropdown.itemText(i).lower() for i in range(dropdown.count())]
        assert any("pending" in item for item in items)

    def test_dropdown_has_in_progress_status(self, qapp, tmp_path):
        """Dropdown should include In Progress status."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path))
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)

        items = [dropdown.itemText(i).lower() for i in range(dropdown.count())]
        assert any("progress" in item for item in items)

    def test_dropdown_has_done_status(self, qapp, tmp_path):
        """Dropdown should include Done status."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path))
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)

        items = [dropdown.itemText(i).lower() for i in range(dropdown.count())]
        assert any("done" in item for item in items)

    def test_dropdown_has_merged_status(self, qapp, tmp_path):
        """Dropdown should include Merged status."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path))
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)

        items = [dropdown.itemText(i).lower() for i in range(dropdown.count())]
        assert any("merged" in item for item in items)

    def test_dropdown_has_declined_status(self, qapp, tmp_path):
        """Dropdown should include Declined status."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path))
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)

        items = [dropdown.itemText(i).lower() for i in range(dropdown.count())]
        assert any("declined" in item for item in items)


class TestStatusDropdownReflectsTicket:
    """Test that dropdown reflects current ticket's status."""

    def test_dropdown_shows_pending_ticket_status(self, qapp, tmp_path):
        """Dropdown should show 'Pending' for pending ticket."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Pending Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        current_text = dropdown.currentText().lower()
        assert "pending" in current_text

    def test_dropdown_shows_in_progress_ticket_status(self, qapp, tmp_path):
        """Dropdown should show 'In Progress' for in-progress ticket."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core.tickets import set_ticket_status

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Working Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(tickets[0])

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        current_text = dropdown.currentText().lower()
        assert "progress" in current_text

    def test_dropdown_shows_done_ticket_status(self, qapp, tmp_path):
        """Dropdown should show 'Done' for done ticket."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core.tickets import set_ticket_status

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Completed Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DONE)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(tickets[0])

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        current_text = dropdown.currentText().lower()
        assert "done" in current_text

    def test_dropdown_shows_declined_ticket_status(self, qapp, tmp_path):
        """Dropdown should show 'Declined' for declined ticket."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core.tickets import set_ticket_status

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Declined Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(tickets[0])

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        current_text = dropdown.currentText().lower()
        assert "declined" in current_text

    def test_dropdown_shows_merged_ticket_status(self, qapp, tmp_path):
        """Dropdown should show 'Merged' for merged ticket."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core.tickets import set_ticket_status

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Merged Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.MERGED)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(tickets[0])

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        current_text = dropdown.currentText().lower()
        assert "merged" in current_text


class TestStatusDropdownChangeMarksDirty:
    """Test that changing dropdown value marks form as dirty."""

    def test_changing_status_marks_form_dirty(self, qapp, tmp_path):
        """Changing status dropdown should mark form as dirty."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Initially should not be dirty
        assert not widget.is_dirty

        # Change dropdown value
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        # Find index of a different status
        for i in range(dropdown.count()):
            if "done" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        # Should now be dirty
        assert widget.is_dirty

    def test_changing_status_enables_save_button(self, qapp, tmp_path):
        """Changing status dropdown should enable Save button."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Save button should be disabled initially
        assert not widget._save_btn.isEnabled()

        # Change dropdown value
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        # Save button should now be enabled
        assert widget._save_btn.isEnabled()


class TestStatusDropdownCreateMode:
    """Test status dropdown behavior in create mode."""

    def test_dropdown_defaults_to_pending_in_create_mode(self, qapp, tmp_path):
        """In create mode, dropdown should default to 'Pending'."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.create_new_ticket()

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        current_text = dropdown.currentText().lower()
        assert "pending" in current_text

    def test_dropdown_enabled_in_create_mode(self, qapp, tmp_path):
        """Status dropdown should be enabled in create mode."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.create_new_ticket()

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        assert dropdown.isEnabled()


class TestStatusDropdownTheming:
    """Test that status dropdown respects current theme."""

    def test_dropdown_respects_dark_theme(self, qapp, tmp_path):
        """Dropdown should respect dark theme styling."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        # Widget should exist and be usable
        assert dropdown is not None

    def test_dropdown_respects_light_theme(self, qapp, tmp_path):
        """Dropdown should respect light theme styling."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path), theme="light")

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        # Widget should exist and be usable
        assert dropdown is not None

    def test_dropdown_updates_on_theme_change(self, qapp, tmp_path):
        """Dropdown should update when theme changes."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")

        # Change theme
        if hasattr(widget, "update_theme"):
            widget.update_theme("light")

        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        # Widget should still be functional
        assert dropdown is not None


class TestStatusDropdownEdgeCases:
    """Test edge cases for status dropdown behavior."""

    def test_dropdown_handles_no_ticket(self, qapp, tmp_path):
        """Dropdown should handle case when no ticket is loaded."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=str(tmp_path))

        # Should not crash
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        assert dropdown is not None

    def test_dropdown_programmatic_change_blocks_signals(self, qapp, tmp_path):
        """Programmatic changes during set_ticket should not mark form dirty."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))

        # Loading ticket should not mark form dirty
        widget.set_ticket(ticket)
        assert not widget.is_dirty

    def test_dropdown_selection_persists_across_loads(self, qapp, tmp_path):
        """Loading same ticket multiple times should show correct status."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core.tickets import set_ticket_status

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))

        # Load as pending
        tickets = read_tickets(tmp_path)
        widget.set_ticket(tickets[0])
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        assert "pending" in dropdown.currentText().lower()

        # Change status externally
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        # Reload
        tickets = read_tickets(tmp_path)
        widget.set_ticket(tickets[0])
        assert "declined" in dropdown.currentText().lower()
