"""Integration tests for pending ticket display in light mode sidebar.

This test file verifies that pending tickets are displayed with the new
darker color in the ticket sidebar widget when using light theme:
- Sidebar displays pending tickets with #2E3440 color in light mode
- Theme switching preserves correct pending colors
- Multiple pending tickets all use the new color
- Integration with run status still works correctly
"""

from __future__ import annotations

from pathlib import Path
import pytest

from levelup.core.tickets import add_ticket

pytestmark = pytest.mark.regression

def _can_import_pyqt6() -> bool:
    """Check if PyQt6 is available."""
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def _ensure_qapp():
    """Ensure QApplication exists."""
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestPendingTicketSidebarLightMode:
    """Test pending tickets display with new color in light mode sidebar."""

    def test_pending_ticket_displays_with_new_color_in_light_mode(self):
        """Pending ticket should display with #2E3440 color in light mode."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
        ]

        widget.set_tickets(tickets)

        item = widget._list.item(0)
        color = item.foreground().color()
        assert color.name().upper() == "#2E3440", \
            f"Pending ticket should use #2E3440 in light mode, got {color.name()}"

    def test_multiple_pending_tickets_all_use_new_color_light_mode(self):
        """All pending tickets should use #2E3440 in light mode."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Pending 1", status=TicketStatus.PENDING),
            Ticket(number=2, title="Pending 2", status=TicketStatus.PENDING),
            Ticket(number=3, title="Pending 3", status=TicketStatus.PENDING),
        ]

        widget.set_tickets(tickets)

        # All pending tickets should have the same new color
        for i in range(3):
            item = widget._list.item(i)
            color = item.foreground().color()
            assert color.name().upper() == "#2E3440", \
                f"Ticket {i+1} should use #2E3440 in light mode"

    def test_pending_ticket_in_dark_mode_uses_old_color(self):
        """Pending ticket in dark mode should still use #CDD6F4."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
        ]

        widget.set_tickets(tickets)

        item = widget._list.item(0)
        color = item.foreground().color()
        assert color.name().upper() == "#CDD6F4", \
            f"Pending ticket should use #CDD6F4 in dark mode, got {color.name()}"

    def test_theme_switch_from_dark_to_light_updates_pending_color(self):
        """Switching from dark to light theme should update pending color."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
        ]

        widget.set_tickets(tickets)

        # Initially dark mode color
        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#CDD6F4"

        # Switch to light mode
        widget.update_theme("light")

        # Should now use light mode color
        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#2E3440", \
            "Should use new light mode color after theme switch"

    def test_theme_switch_from_light_to_dark_updates_pending_color(self):
        """Switching from light to dark theme should update pending color."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
        ]

        widget.set_tickets(tickets)

        # Initially light mode color
        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#2E3440"

        # Switch to dark mode
        widget.update_theme("dark")

        # Should now use dark mode color
        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#CDD6F4", \
            "Should use dark mode color after theme switch"

    def test_pending_with_run_status_ignores_run_in_light_mode(self):
        """Pending ticket with run status should ignore it and use pending color in light mode."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
        ]
        run_status_map = {1: "running"}  # Should be ignored for pending

        widget.set_tickets(tickets, run_status_map=run_status_map)

        item = widget._list.item(0)
        color = item.foreground().color()
        # Should use pending color, not running blue
        assert color.name().upper() == "#2E3440", \
            "Pending ticket should use pending color, not run status color"

    def test_mixed_ticket_statuses_in_light_mode(self):
        """Mixed ticket statuses should each use correct light mode colors."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="In Progress", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Done", status=TicketStatus.DONE),
            Ticket(number=4, title="Merged", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        # Check each status has correct color
        assert widget._list.item(0).foreground().color().name().upper() == "#2E3440"  # Pending (NEW)
        assert widget._list.item(1).foreground().color().name().upper() == "#F39C12"  # In Progress
        assert widget._list.item(2).foreground().color().name().upper() == "#27AE60"  # Done
        assert widget._list.item(3).foreground().color().name().upper() == "#95A5A6"  # Merged

    def test_pending_color_not_affected_by_other_ticket_colors(self):
        """Pending ticket color should be independent of other ticket colors."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")

        # First, add only pending tickets
        pending_tickets = [
            Ticket(number=1, title="Pending 1", status=TicketStatus.PENDING),
        ]
        widget.set_tickets(pending_tickets)
        pending_color = widget._list.item(0).foreground().color().name().upper()

        # Then, add mixed tickets
        mixed_tickets = [
            Ticket(number=1, title="Pending 1", status=TicketStatus.PENDING),
            Ticket(number=2, title="Done", status=TicketStatus.DONE),
            Ticket(number=3, title="In Progress", status=TicketStatus.IN_PROGRESS),
        ]
        widget.set_tickets(mixed_tickets)

        # Pending color should remain the same
        assert widget._list.item(0).foreground().color().name().upper() == pending_color
        assert widget._list.item(0).foreground().color().name().upper() == "#2E3440"

    def test_pending_color_preserved_on_ticket_list_refresh(self):
        """Pending color should be preserved when ticket list is refreshed."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
        ]

        # Set tickets multiple times
        for _ in range(5):
            widget.set_tickets(tickets)
            item = widget._list.item(0)
            assert item.foreground().color().name().upper() == "#2E3440", \
                "Pending color should be consistent across refreshes"

    def test_pending_color_with_empty_run_status_map(self):
        """Pending ticket should use correct color with empty run status map."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
        ]
        run_status_map = {}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#2E3440"

    def test_pending_color_with_none_run_status_map(self):
        """Pending ticket should use correct color with None run status map."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
        ]

        widget.set_tickets(tickets, run_status_map=None)

        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#2E3440"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestPendingTicketSidebarSelection:
    """Test that selection is preserved with new pending color."""

    def test_selection_preserved_when_pending_ticket_selected(self):
        """Selection should be preserved when pending ticket is selected."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Pending 1", status=TicketStatus.PENDING),
            Ticket(number=2, title="Pending 2", status=TicketStatus.PENDING),
        ]

        widget.set_tickets(tickets)
        widget._list.setCurrentRow(1)

        # Refresh tickets
        widget.set_tickets(tickets)

        # Selection should be preserved
        assert widget._list.currentRow() == 1

    def test_pending_ticket_color_when_selected(self):
        """Pending ticket should maintain color when selected."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
        ]

        widget.set_tickets(tickets)
        widget._list.setCurrentRow(0)

        item = widget._list.item(0)
        # Foreground color should still be the pending color
        assert item.foreground().color().name().upper() == "#2E3440"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestPendingTicketColorRegressionPrevention:
    """Test to prevent regression of pending ticket color in light mode."""

    def test_pending_color_never_reverts_to_4C566A(self):
        """Ensure pending color in light mode never reverts to old #4C566A."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
        ]

        # Try various operations that might cause regression
        widget.set_tickets(tickets)
        item = widget._list.item(0)
        color = item.foreground().color().name().upper()
        assert color != "#4C566A", \
            "Color should not be old value #4C566A"
        assert color == "#2E3440", \
            f"Color should be new value #2E3440, got {color}"

        # Theme switch and back
        widget.update_theme("dark")
        widget.update_theme("light")
        item = widget._list.item(0)
        color = item.foreground().color().name().upper()
        assert color != "#4C566A", \
            "Color should not revert to #4C566A after theme switch"
        assert color == "#2E3440"

        # Refresh
        widget.set_tickets(tickets)
        item = widget._list.item(0)
        color = item.foreground().color().name().upper()
        assert color != "#4C566A", \
            "Color should not revert to #4C566A after refresh"
        assert color == "#2E3440"

    def test_light_theme_constant_not_4C566A(self):
        """Verify the constant itself is not #4C566A."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        assert _LIGHT_TICKET_STATUS_COLORS["pending"] != "#4C566A", \
            "Constant should be updated from old value"
        assert _LIGHT_TICKET_STATUS_COLORS["pending"] == "#2E3440", \
            "Constant should be new value #2E3440"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestOtherTicketStatusesUnchangedInLightMode:
    """Test that other ticket statuses are not affected by pending color change."""

    def test_in_progress_color_unchanged_in_light_mode(self):
        """In progress ticket color should be unchanged in light mode."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="In Progress", status=TicketStatus.IN_PROGRESS),
        ]

        widget.set_tickets(tickets)

        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#F39C12"

    def test_done_color_unchanged_in_light_mode(self):
        """Done ticket color should be unchanged in light mode."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Done", status=TicketStatus.DONE),
        ]

        widget.set_tickets(tickets)

        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#27AE60"

    def test_merged_color_unchanged_in_light_mode(self):
        """Merged ticket color should be unchanged in light mode."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Merged", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#95A5A6"

    def test_all_dark_mode_colors_unchanged(self):
        """All ticket colors in dark mode should be unchanged."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="In Progress", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Done", status=TicketStatus.DONE),
            Ticket(number=4, title="Merged", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        assert widget._list.item(0).foreground().color().name().upper() == "#CDD6F4"  # Pending
        assert widget._list.item(1).foreground().color().name().upper() == "#E6A817"  # In Progress
        assert widget._list.item(2).foreground().color().name().upper() == "#2ECC71"  # Done
        assert widget._list.item(3).foreground().color().name().upper() == "#6C7086"  # Merged


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestMainWindowIntegrationWithNewPendingColor:
    """Test MainWindow integration with new pending color."""

    def test_main_window_displays_pending_with_new_color_light_mode(self, tmp_path):
        """MainWindow should display pending tickets with #2E3440 in light mode."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from unittest.mock import patch

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Pending ticket 1")
        add_ticket(project_path, "Pending ticket 2")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Update sidebar theme to light mode
        window._sidebar.update_theme("light")
        window._refresh_tickets()

        # Both pending tickets should use new color
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#2E3440"
        assert window._sidebar._list.item(1).foreground().color().name().upper() == "#2E3440"

    def test_main_window_theme_switch_updates_pending_color(self, tmp_path):
        """MainWindow theme switch should update pending ticket color."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from unittest.mock import patch

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Pending ticket")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        window._refresh_tickets()

        # Initially dark mode (default)
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#CDD6F4"

        # Switch to light mode
        window._sidebar.update_theme("light")

        # Should now use light mode color
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#2E3440"
