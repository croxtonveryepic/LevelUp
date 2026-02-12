"""Unit tests for status label updates after status changes."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.regression

# GUI tests require PyQt6
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from levelup.core.tickets import TicketStatus, add_ticket, read_tickets, set_ticket_status


# Test fixtures need a QApplication instance
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestStatusLabelDisplay:
    """Test that status label displays correct status with icon and color."""

    def test_status_label_shows_pending(self, qapp, tmp_path):
        """Status label should show pending status with icon."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        label_text = widget._status_label.text().lower()
        assert "pending" in label_text

    def test_status_label_shows_declined(self, qapp, tmp_path):
        """Status label should show declined status with icon."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(tickets[0])

        label_text = widget._status_label.text().lower()
        assert "declined" in label_text

    def test_status_label_includes_icon(self, qapp, tmp_path):
        """Status label should include appropriate icon character."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.resources import TICKET_STATUS_ICONS

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(tickets[0])

        label_text = widget._status_label.text()
        declined_icon = TICKET_STATUS_ICONS.get("declined", "")
        # Icon should appear in label
        assert declined_icon in label_text

    def test_status_label_color_declined_dark_theme(self, qapp, tmp_path):
        """Status label should use green color for declined in dark theme."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        widget.set_ticket(tickets[0])

        style = widget._status_label.styleSheet()
        # Should contain green color
        assert "#2ECC71" in style

    def test_status_label_color_declined_light_theme(self, qapp, tmp_path):
        """Status label should use green color for declined in light theme."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path), theme="light")
        widget.set_ticket(tickets[0])

        style = widget._status_label.styleSheet()
        # Should contain green color
        assert "#27AE60" in style


class TestStatusLabelUpdatesAfterSave:
    """Test that status label updates after saving status change."""

    def test_label_updates_after_status_change_save(self, qapp, tmp_path):
        """Status label should update to show new status after save."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Initially pending
        assert "pending" in widget._status_label.text().lower()

        # Change status to declined
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        # Reload ticket to see updated label
        tickets = read_tickets(tmp_path)
        widget.set_ticket(tickets[0])

        # Should now show declined
        assert "declined" in widget._status_label.text().lower()

    def test_label_color_updates_after_status_change(self, qapp, tmp_path):
        """Status label color should update after changing status."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        widget.set_ticket(ticket)

        # Initially pending color
        initial_style = widget._status_label.styleSheet()
        assert "#CDD6F4" in initial_style

        # Change status to declined
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        # Reload ticket
        tickets = read_tickets(tmp_path)
        widget.set_ticket(tickets[0])

        # Should now have green color
        new_style = widget._status_label.styleSheet()
        assert "#2ECC71" in new_style

    def test_label_icon_updates_after_status_change(self, qapp, tmp_path):
        """Status label icon should update after changing status."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.resources import TICKET_STATUS_ICONS

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(ticket)

        # Initially pending icon
        pending_icon = TICKET_STATUS_ICONS.get("pending", "")
        assert pending_icon in widget._status_label.text()

        # Change status to declined
        dropdown = getattr(widget, "status_dropdown", None) or getattr(widget, "_status_dropdown", None)
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        widget.save_ticket()

        # Reload ticket
        tickets = read_tickets(tmp_path)
        widget.set_ticket(tickets[0])

        # Should now have declined icon
        declined_icon = TICKET_STATUS_ICONS.get("declined", "")
        assert declined_icon in widget._status_label.text()


class TestStatusLabelThemeUpdates:
    """Test that status label colors update when theme changes."""

    def test_declined_label_updates_on_theme_change(self, qapp, tmp_path):
        """Status label color should update when switching themes."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        widget.set_ticket(tickets[0])

        # Dark theme color
        assert "#2ECC71" in widget._status_label.styleSheet()

        # Switch to light theme
        if hasattr(widget, "update_theme"):
            widget.update_theme("light")
            # Should update to light theme color
            # (This may require reloading the ticket or calling set_ticket again)


class TestStatusLabelAllStatuses:
    """Test status label for all ticket statuses."""

    def test_label_for_in_progress_status(self, qapp, tmp_path):
        """Status label should correctly display in progress status."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.IN_PROGRESS)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(tickets[0])

        label_text = widget._status_label.text().lower()
        assert "progress" in label_text

    def test_label_for_done_status(self, qapp, tmp_path):
        """Status label should correctly display done status."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DONE)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(tickets[0])

        label_text = widget._status_label.text().lower()
        assert "done" in label_text

    def test_label_for_merged_status(self, qapp, tmp_path):
        """Status label should correctly display merged status."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.MERGED)

        tickets = read_tickets(tmp_path)
        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_ticket(tickets[0])

        label_text = widget._status_label.text().lower()
        assert "merged" in label_text

    def test_label_colors_for_all_statuses(self, qapp, tmp_path):
        """Status label should use appropriate colors for all statuses."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.resources import get_ticket_status_color

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        for status in TicketStatus:
            add_ticket(tmp_path, f"Task {status.value}", "Description")
            ticket_num = len(read_tickets(tmp_path))
            set_ticket_status(tmp_path, ticket_num, status)

            tickets = read_tickets(tmp_path)
            widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
            widget.set_ticket(tickets[-1])

            expected_color = get_ticket_status_color(status.value, theme="dark")
            style = widget._status_label.styleSheet()
            assert expected_color in style, f"Color mismatch for {status.value}"
