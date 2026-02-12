"""Tests for ticket sidebar color changes based on run execution state.

This test file covers the requirements for dynamically coloring tickets
in the sidebar based on both ticket status and associated run status:
- Blue when run is actively running
- Yellow-orange when run is waiting for user input
- Default yellow-orange for in progress tickets without active runs
- Other ticket statuses remain unchanged
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest

from levelup.core.tickets import add_ticket, set_ticket_status, TicketStatus

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


class TestGetTicketStatusColorWithRunStatus:
    """Test get_ticket_status_color() with optional run_status parameter."""

    def test_accepts_run_status_parameter(self):
        """get_ticket_status_color() should accept optional run_status parameter."""
        from levelup.gui.resources import get_ticket_status_color

        # Should not raise when called with run_status
        color = get_ticket_status_color("in progress", theme="dark", run_status="running")
        assert isinstance(color, str)
        assert color.startswith("#")

    def test_in_progress_with_running_returns_blue_dark_theme(self):
        """In progress ticket with running status should return blue in dark theme."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("in progress", theme="dark", run_status="running")
        # Expected: #4A90D9 (blue, matches run "running" color in dark theme)
        assert color == "#4A90D9"

    def test_in_progress_with_running_returns_blue_light_theme(self):
        """In progress ticket with running status should return blue in light theme."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("in progress", theme="light", run_status="running")
        # Expected: #3498DB (blue, matches run "running" color in light theme)
        assert color == "#3498DB"

    def test_in_progress_with_waiting_for_input_returns_yellow_orange_dark_theme(self):
        """In progress ticket with waiting_for_input status should return yellow-orange in dark theme."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("in progress", theme="dark", run_status="waiting_for_input")
        # Expected: #E6A817 (yellow-orange, matches run "waiting_for_input" color in dark theme)
        assert color == "#E6A817"

    def test_in_progress_with_waiting_for_input_returns_yellow_orange_light_theme(self):
        """In progress ticket with waiting_for_input status should return yellow-orange in light theme."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("in progress", theme="light", run_status="waiting_for_input")
        # Expected: #F39C12 (orange, matches run "waiting_for_input" color in light theme)
        assert color == "#F39C12"

    def test_in_progress_without_run_status_returns_default_yellow_orange_dark_theme(self):
        """In progress ticket without run status should return default yellow-orange in dark theme."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("in progress", theme="dark")
        # Expected: #E6A817 (default in progress color for dark theme)
        assert color == "#E6A817"

    def test_in_progress_without_run_status_returns_default_orange_light_theme(self):
        """In progress ticket without run status should return default orange in light theme."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("in progress", theme="light")
        # Expected: #F39C12 (default in progress color for light theme)
        assert color == "#F39C12"

    def test_in_progress_with_none_run_status_returns_default(self):
        """In progress ticket with None run_status should return default color."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("in progress", theme="dark", run_status=None)
        # Should behave the same as not providing run_status
        assert color == "#E6A817"

    def test_pending_with_run_status_ignores_run_status(self):
        """Pending ticket should ignore run_status and return pending color."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("pending", theme="dark", run_status="running")
        # Should return pending color, not run status color
        assert color == "#CDD6F4"  # Pending color in dark theme

    def test_done_with_run_status_ignores_run_status(self):
        """Done ticket should ignore run_status and return done color."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("done", theme="dark", run_status="running")
        # Should return done color (green), not run status color
        assert color == "#2ECC71"

    def test_merged_with_run_status_ignores_run_status(self):
        """Merged ticket should ignore run_status and return merged color."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("merged", theme="dark", run_status="running")
        # Should return merged color, not run status color
        assert color == "#6C7086"

    def test_in_progress_with_other_run_status_returns_default(self):
        """In progress ticket with non-active run status should return default color."""
        from levelup.gui.resources import get_ticket_status_color

        # Test with various non-active run statuses
        for run_status in ["completed", "failed", "aborted", "paused", "pending"]:
            color = get_ticket_status_color("in progress", theme="dark", run_status=run_status)
            # Should return default in progress color
            assert color == "#E6A817", f"Failed for run_status={run_status}"

    def test_backward_compatibility_no_run_status_parameter(self):
        """Function should work exactly as before when run_status is not provided."""
        from levelup.gui.resources import get_ticket_status_color

        # Test all ticket statuses work without run_status parameter
        expected_dark = {
            "pending": "#CDD6F4",
            "in progress": "#E6A817",
            "done": "#2ECC71",
            "merged": "#6C7086",
        }

        for status, expected_color in expected_dark.items():
            color = get_ticket_status_color(status, theme="dark")
            assert color == expected_color, f"Backward compatibility failed for {status}"

    def test_empty_run_status_string_returns_default(self):
        """Empty string for run_status should be treated as no run status."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("in progress", theme="dark", run_status="")
        # Should return default in progress color
        assert color == "#E6A817"

    def test_unknown_run_status_returns_default(self):
        """Unknown run_status value should return default ticket color."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("in progress", theme="dark", run_status="unknown_status")
        # Should return default in progress color
        assert color == "#E6A817"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestTicketSidebarSetTicketsWithRunStatus:
    """Test TicketSidebarWidget.set_tickets() with run status mapping."""

    def test_set_tickets_accepts_run_status_map_parameter(self):
        """set_tickets() should accept optional run_status_map parameter."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        # This test will fail until the implementation is added
        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Test ticket", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {1: "running"}

        # Should not raise when called with run_status_map
        widget.set_tickets(tickets, run_status_map=run_status_map)

    def test_set_tickets_colors_running_ticket_blue_dark_theme(self):
        """Ticket with running status should be colored blue in dark theme."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Running ticket", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {1: "running"}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Get the item from the list widget and check its color
        item = widget._list.item(0)
        color = item.foreground().color()
        # Expected: blue (#4A90D9)
        assert color.name().upper() == "#4A90D9"

    def test_set_tickets_colors_running_ticket_blue_light_theme(self):
        """Ticket with running status should be colored blue in light theme."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Running ticket", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {1: "running"}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        item = widget._list.item(0)
        color = item.foreground().color()
        # Expected: blue (#3498DB)
        assert color.name().upper() == "#3498DB"

    def test_set_tickets_colors_waiting_ticket_yellow_orange_dark_theme(self):
        """Ticket with waiting_for_input status should be colored yellow-orange in dark theme."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Waiting ticket", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {1: "waiting_for_input"}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        item = widget._list.item(0)
        color = item.foreground().color()
        # Expected: yellow-orange (#E6A817)
        assert color.name().upper() == "#E6A817"

    def test_set_tickets_colors_waiting_ticket_orange_light_theme(self):
        """Ticket with waiting_for_input status should be colored orange in light theme."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="light")
        tickets = [
            Ticket(number=1, title="Waiting ticket", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {1: "waiting_for_input"}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        item = widget._list.item(0)
        color = item.foreground().color()
        # Expected: orange (#F39C12)
        assert color.name().upper() == "#F39C12"

    def test_set_tickets_in_progress_without_run_uses_default_color(self):
        """In progress ticket without run status should use default color."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="In progress ticket", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {}  # No run status for this ticket

        widget.set_tickets(tickets, run_status_map=run_status_map)

        item = widget._list.item(0)
        color = item.foreground().color()
        # Expected: default yellow-orange (#E6A817)
        assert color.name().upper() == "#E6A817"

    def test_set_tickets_without_run_status_map_uses_ticket_colors(self):
        """set_tickets() without run_status_map should use ticket status colors only."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="In progress", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Done", status=TicketStatus.DONE),
        ]

        # Call without run_status_map parameter
        widget.set_tickets(tickets)

        # Check colors match ticket status only
        assert widget._list.item(0).foreground().color().name().upper() == "#CDD6F4"  # Pending
        assert widget._list.item(1).foreground().color().name().upper() == "#E6A817"  # In progress
        assert widget._list.item(2).foreground().color().name().upper() == "#2ECC71"  # Done

    def test_set_tickets_pending_status_ignores_run_status(self):
        """Pending ticket should ignore run status and use pending color."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
        ]
        run_status_map = {1: "running"}  # Should be ignored

        widget.set_tickets(tickets, run_status_map=run_status_map)

        item = widget._list.item(0)
        color = item.foreground().color()
        # Expected: pending color (#CDD6F4), not blue
        assert color.name().upper() == "#CDD6F4"

    def test_set_tickets_done_status_ignores_run_status(self):
        """Done ticket should ignore run status and use done color."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Done ticket", status=TicketStatus.DONE),
        ]
        run_status_map = {1: "running"}  # Should be ignored

        widget.set_tickets(tickets, run_status_map=run_status_map)

        item = widget._list.item(0)
        color = item.foreground().color()
        # Expected: green (#2ECC71), not blue
        assert color.name().upper() == "#2ECC71"

    def test_set_tickets_merged_status_ignores_run_status(self):
        """Merged ticket should ignore run status and use merged color."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Merged ticket", status=TicketStatus.MERGED),
        ]
        run_status_map = {1: "running"}  # Should be ignored

        widget.set_tickets(tickets, run_status_map=run_status_map)

        item = widget._list.item(0)
        color = item.foreground().color()
        # Expected: merged color (#6C7086), not blue
        assert color.name().upper() == "#6C7086"

    def test_set_tickets_multiple_tickets_different_run_statuses(self):
        """Multiple tickets with different run statuses should have correct colors."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Running", status=TicketStatus.IN_PROGRESS),
            Ticket(number=2, title="Waiting", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="In progress no run", status=TicketStatus.IN_PROGRESS),
            Ticket(number=4, title="Done", status=TicketStatus.DONE),
        ]
        run_status_map = {
            1: "running",
            2: "waiting_for_input",
            # Ticket 3 has no run status
            # Ticket 4 should ignore run status
        }

        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Check each ticket has the correct color
        assert widget._list.item(0).foreground().color().name().upper() == "#4A90D9"  # Blue (running)
        assert widget._list.item(1).foreground().color().name().upper() == "#E6A817"  # Yellow-orange (waiting)
        assert widget._list.item(2).foreground().color().name().upper() == "#E6A817"  # Yellow-orange (default in progress)
        assert widget._list.item(3).foreground().color().name().upper() == "#2ECC71"  # Green (done)

    def test_set_tickets_run_status_map_empty_dict_uses_ticket_colors(self):
        """Empty run_status_map dict should use ticket status colors only."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="In progress", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        item = widget._list.item(0)
        color = item.foreground().color()
        # Expected: default yellow-orange (#E6A817)
        assert color.name().upper() == "#E6A817"

    def test_set_tickets_run_status_map_none_uses_ticket_colors(self):
        """None run_status_map should use ticket status colors only."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="In progress", status=TicketStatus.IN_PROGRESS),
        ]

        widget.set_tickets(tickets, run_status_map=None)

        item = widget._list.item(0)
        color = item.foreground().color()
        # Expected: default yellow-orange (#E6A817)
        assert color.name().upper() == "#E6A817"

    def test_update_theme_reapplies_colors_with_run_status(self):
        """update_theme() should reapply colors based on run status in new theme."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Running ticket", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {1: "running"}

        # Set tickets with dark theme
        widget.set_tickets(tickets, run_status_map=run_status_map)
        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#4A90D9"  # Dark blue

        # Update to light theme
        widget.update_theme("light")

        # Color should now be light theme blue
        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#3498DB"  # Light blue

    def test_backward_compatibility_existing_code_still_works(self):
        """Existing code that calls set_tickets without run_status_map should still work."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Test", status=TicketStatus.PENDING),
        ]

        # This is how existing code calls it (without run_status_map)
        widget.set_tickets(tickets)

        # Should work exactly as before
        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#CDD6F4"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestMainWindowRefreshTicketsWithRunStatus:
    """Test MainWindow._refresh_tickets() passes run status to sidebar."""

    def test_refresh_tickets_creates_run_status_mapping(self, tmp_path):
        """_refresh_tickets() should create run status mapping from self._runs."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.state.models import RunRecord

        # Create temporary DB
        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        # Create window with project path
        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Test ticket 1")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)
        add_ticket(project_path, "Test ticket 2")

        # Create window with patched refresh to avoid auto-refresh
        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Set up mock runs
        window._runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                project_path=str(project_path),
                status="running",
                ticket_number=1,
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
            RunRecord(
                run_id="run2",
                task_title="Task 2",
                project_path=str(project_path),
                status="waiting_for_input",
                ticket_number=2,
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
        ]

        # Call _refresh_tickets
        window._refresh_tickets()

        # Verify sidebar received run status mapping
        # The sidebar should have colored ticket 1 blue and ticket 2 yellow-orange
        item1 = window._sidebar._list.item(0)
        item2 = window._sidebar._list.item(1)

        # Ticket 1 (in progress with running run) should be blue
        assert item1.foreground().color().name().upper() == "#4A90D9"

        # Ticket 2 (pending status, should ignore run status) should be pending color
        # Note: Ticket 2 is not "in progress" so run status shouldn't affect it
        assert item2.foreground().color().name().upper() == "#CDD6F4"  # Pending color

    def test_refresh_tickets_only_includes_active_run_statuses(self, tmp_path):
        """_refresh_tickets() should only include running/waiting_for_input statuses."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.state.models import RunRecord

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        add_ticket(project_path, "Ticket 1")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)
        add_ticket(project_path, "Ticket 2")
        set_ticket_status(project_path, 2, TicketStatus.IN_PROGRESS)
        add_ticket(project_path, "Ticket 3")
        set_ticket_status(project_path, 3, TicketStatus.IN_PROGRESS)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Set up runs with various statuses
        window._runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                project_path=str(project_path),
                status="running",  # Should be included
                ticket_number=1,
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
            RunRecord(
                run_id="run2",
                task_title="Task 2",
                project_path=str(project_path),
                status="completed",  # Should NOT be included
                ticket_number=2,
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
            RunRecord(
                run_id="run3",
                task_title="Task 3",
                project_path=str(project_path),
                status="failed",  # Should NOT be included
                ticket_number=3,
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
        ]

        window._refresh_tickets()

        # Ticket 1 should be blue (running)
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#4A90D9"

        # Tickets 2 and 3 should be default yellow-orange (no active run)
        assert window._sidebar._list.item(1).foreground().color().name().upper() == "#E6A817"
        assert window._sidebar._list.item(2).foreground().color().name().upper() == "#E6A817"

    def test_refresh_tickets_handles_no_runs(self, tmp_path):
        """_refresh_tickets() should handle case with no runs gracefully."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        add_ticket(project_path, "Test ticket")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        window._runs = []  # No runs

        # Should not raise
        window._refresh_tickets()

        # Ticket should use default in progress color
        item = window._sidebar._list.item(0)
        assert item.foreground().color().name().upper() == "#E6A817"

    def test_refresh_tickets_handles_runs_without_ticket_numbers(self, tmp_path):
        """_refresh_tickets() should handle runs without ticket_number field."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.state.models import RunRecord

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        add_ticket(project_path, "Test ticket")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Set up run without ticket_number
        window._runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                project_path=str(project_path),
                status="running",
                ticket_number=None,  # No ticket association
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
        ]

        # Should not raise
        window._refresh_tickets()

        # Ticket should use default color (no run status)
        item = window._sidebar._list.item(0)
        assert item.foreground().color().name().upper() == "#E6A817"

    def test_refresh_tickets_handles_multiple_runs_same_ticket(self, tmp_path):
        """_refresh_tickets() should handle multiple runs for same ticket (use most recent)."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.state.models import RunRecord

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        add_ticket(project_path, "Test ticket")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Set up multiple runs for same ticket (only latest active run should matter)
        window._runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                project_path=str(project_path),
                status="completed",  # Old completed run
                ticket_number=1,
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
            RunRecord(
                run_id="run2",
                task_title="Task 2",
                project_path=str(project_path),
                status="waiting_for_input",  # Current active run
                ticket_number=1,
                started_at="2024-01-01T01:00:00",
                updated_at="2024-01-01T01:00:00",
            ),
        ]

        window._refresh_tickets()

        # Ticket should be yellow-orange (waiting_for_input), not default
        item = window._sidebar._list.item(0)
        assert item.foreground().color().name().upper() == "#E6A817"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestEdgeCasesAndErrorConditions:
    """Test edge cases and error conditions."""

    def test_get_ticket_status_color_invalid_ticket_status(self):
        """Invalid ticket status should return default color."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("invalid_status", theme="dark")
        # Should return default color
        assert color == "#CDD6F4"  # Default dark theme color

    def test_get_ticket_status_color_invalid_theme(self):
        """Invalid theme should fall back to dark theme."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("in progress", theme="invalid_theme")
        # Should return dark theme color
        assert color == "#E6A817"

    def test_set_tickets_preserves_selection_with_run_status_map(self):
        """set_tickets() with run_status_map should preserve current selection."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Ticket 1", status=TicketStatus.IN_PROGRESS),
            Ticket(number=2, title="Ticket 2", status=TicketStatus.IN_PROGRESS),
        ]

        # Set initial tickets and select second one
        widget.set_tickets(tickets)
        widget._list.setCurrentRow(1)

        # Update with run status map
        run_status_map = {1: "running"}
        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Selection should be preserved
        assert widget._list.currentRow() == 1

    def test_sidebar_stores_run_status_map_for_update_theme(self):
        """Sidebar should store run_status_map to reapply on theme change."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Running", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {1: "running"}

        # Set tickets with run status
        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Verify dark theme color (blue)
        assert widget._list.item(0).foreground().color().name().upper() == "#4A90D9"

        # Change theme
        widget.update_theme("light")

        # Color should update to light theme blue, not default orange
        # This means the widget remembered the run status map
        assert widget._list.item(0).foreground().color().name().upper() == "#3498DB"

    def test_set_tickets_with_empty_tickets_list(self):
        """set_tickets() with empty list should handle gracefully."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        widget = TicketSidebarWidget(theme="dark")
        run_status_map = {1: "running"}

        # Should not raise
        widget.set_tickets([], run_status_map=run_status_map)

        # List should be empty
        assert widget._list.count() == 0
