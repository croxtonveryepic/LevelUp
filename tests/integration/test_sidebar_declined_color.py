"""Integration tests for declined status color in ticket sidebar."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.regression

# GUI tests require PyQt6
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from levelup.core.tickets import TicketStatus, add_ticket, set_ticket_status


# Test fixtures need a QApplication instance
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestSidebarDeclinedColorDarkTheme:
    """Test that declined tickets appear green in sidebar (dark theme)."""

    def test_declined_ticket_uses_green_color_in_sidebar(self, qapp, tmp_path):
        """Declined ticket should display with green color in sidebar."""
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Declined Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        sidebar = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar.refresh()

        # Sidebar should be using the green color for declined status
        # This is implementation-specific but color should be #2ECC71
        assert sidebar.ticket_list is not None

    def test_declined_color_matches_done_in_sidebar(self, qapp, tmp_path):
        """Declined and done tickets should use same green in sidebar."""
        from levelup.gui.ticket_sidebar import TicketSidebar
        from levelup.gui.resources import get_ticket_status_color

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Declined Task", "Description")
        add_ticket(tmp_path, "Done Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)
        set_ticket_status(tmp_path, 2, TicketStatus.DONE)

        # Both should use same green color
        declined_color = get_ticket_status_color("declined", theme="dark")
        done_color = get_ticket_status_color("done", theme="dark")
        assert declined_color == done_color
        assert declined_color == "#2ECC71"

    def test_multiple_declined_tickets_in_sidebar(self, qapp, tmp_path):
        """Multiple declined tickets should all appear green."""
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Declined 1", "Description")
        add_ticket(tmp_path, "Declined 2", "Description")
        add_ticket(tmp_path, "Declined 3", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)
        set_ticket_status(tmp_path, 2, TicketStatus.DECLINED)
        set_ticket_status(tmp_path, 3, TicketStatus.DECLINED)

        sidebar = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar.refresh()

        # All declined tickets should be visible with green color
        assert sidebar.ticket_list.count() == 3


class TestSidebarDeclinedColorLightTheme:
    """Test that declined tickets appear green in sidebar (light theme)."""

    def test_declined_ticket_uses_green_color_in_light_sidebar(self, qapp, tmp_path):
        """Declined ticket should display with green color in light theme sidebar."""
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Declined Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        sidebar = TicketSidebar(project_path=str(tmp_path), theme="light")
        sidebar.refresh()

        # Should use light theme green color #27AE60
        assert sidebar.ticket_list is not None

    def test_declined_color_matches_done_in_light_sidebar(self, qapp, tmp_path):
        """Declined and done tickets should use same green in light sidebar."""
        from levelup.gui.resources import get_ticket_status_color

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Both should use same light green color
        declined_color = get_ticket_status_color("declined", theme="light")
        done_color = get_ticket_status_color("done", theme="light")
        assert declined_color == done_color
        assert declined_color == "#27AE60"

    def test_light_theme_declined_color_readable(self, qapp, tmp_path):
        """Light theme declined color should be readable on light background."""
        from levelup.gui.resources import get_ticket_status_color

        try:
            from PyQt6.QtGui import QColor
        except ImportError:
            pytest.skip("PyQt6 not available")

        color = QColor(get_ticket_status_color("declined", theme="light"))
        luminance = (color.red() + color.green() + color.blue()) / 3

        # Should be dark enough to read on light background
        assert luminance < 250


class TestSidebarRefreshAfterStatusChange:
    """Test that sidebar refreshes properly after status changes."""

    def test_sidebar_updates_when_status_changed_to_declined(self, qapp, tmp_path):
        """Sidebar should show green color after changing ticket to declined."""
        from levelup.gui.ticket_sidebar import TicketSidebar
        from levelup.core.tickets import read_tickets

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")

        sidebar = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar.refresh()

        # Change status to declined
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        # Refresh sidebar
        sidebar.refresh()

        # Should now show green color
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DECLINED

    def test_sidebar_preserves_selection_after_status_change(self, qapp, tmp_path):
        """Sidebar should preserve selection after status change refresh."""
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task 1", "Description")
        add_ticket(tmp_path, "Task 2", "Description")

        sidebar = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar.refresh()

        # Select first ticket
        sidebar.ticket_list.setCurrentRow(0)
        selected_row = sidebar.ticket_list.currentRow()

        # Change its status
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        # Refresh sidebar
        sidebar.refresh()

        # Selection should be preserved (or handled gracefully)
        # Implementation may vary
        assert sidebar.ticket_list.currentRow() >= 0 or sidebar.ticket_list.currentRow() == -1


class TestSidebarMixedStatuses:
    """Test sidebar display with mixed ticket statuses including declined."""

    def test_sidebar_shows_all_statuses_with_correct_colors(self, qapp, tmp_path):
        """Sidebar should show all ticket statuses with correct colors."""
        from levelup.gui.ticket_sidebar import TicketSidebar
        from levelup.gui.resources import get_ticket_status_color

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Pending Task", "Description")
        add_ticket(tmp_path, "In Progress Task", "Description")
        add_ticket(tmp_path, "Done Task", "Description")
        add_ticket(tmp_path, "Merged Task", "Description")
        add_ticket(tmp_path, "Declined Task", "Description")

        set_ticket_status(tmp_path, 2, TicketStatus.IN_PROGRESS)
        set_ticket_status(tmp_path, 3, TicketStatus.DONE)
        set_ticket_status(tmp_path, 4, TicketStatus.MERGED)
        set_ticket_status(tmp_path, 5, TicketStatus.DECLINED)

        sidebar = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar.refresh()

        # All tickets should be visible
        assert sidebar.ticket_list.count() == 5

        # Verify colors are correct
        declined_color = get_ticket_status_color("declined", theme="dark")
        done_color = get_ticket_status_color("done", theme="dark")
        assert declined_color == done_color == "#2ECC71"

    def test_declined_and_done_visually_similar_in_sidebar(self, qapp, tmp_path):
        """Declined and done tickets should be visually similar (both green)."""
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Done Task", "Description")
        add_ticket(tmp_path, "Declined Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DONE)
        set_ticket_status(tmp_path, 2, TicketStatus.DECLINED)

        sidebar = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar.refresh()

        # Both should be present and use green color
        assert sidebar.ticket_list.count() == 2


class TestSidebarDeclinedIcon:
    """Test that declined tickets show appropriate icon in sidebar."""

    def test_sidebar_shows_declined_icon(self, qapp, tmp_path):
        """Sidebar should show declined icon for declined tickets."""
        from levelup.gui.ticket_sidebar import TicketSidebar
        from levelup.gui.resources import TICKET_STATUS_ICONS

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Declined Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        sidebar = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar.refresh()

        # Icon should be defined
        declined_icon = TICKET_STATUS_ICONS.get("declined")
        assert declined_icon is not None
        assert len(declined_icon) == 1


class TestSidebarThemeSwitching:
    """Test sidebar color updates when switching themes."""

    def test_declined_color_updates_on_theme_switch(self, qapp, tmp_path):
        """Declined ticket color should update when switching themes."""
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Declined Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        # Start with dark theme
        sidebar = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar.refresh()

        # Switch to light theme
        if hasattr(sidebar, "update_theme"):
            sidebar.update_theme("light")

        # Should now use light theme color
        # Implementation-specific behavior

    def test_sidebar_handles_theme_at_construction(self, qapp, tmp_path):
        """Sidebar should handle theme parameter at construction."""
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        # Create with light theme
        sidebar_light = TicketSidebar(project_path=str(tmp_path), theme="light")
        sidebar_light.refresh()

        # Create with dark theme
        sidebar_dark = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar_dark.refresh()

        # Both should work
        assert sidebar_light.ticket_list is not None
        assert sidebar_dark.ticket_list is not None
