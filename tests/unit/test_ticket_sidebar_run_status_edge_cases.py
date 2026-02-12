"""Additional edge case tests for ticket sidebar run status colors.

This test file provides additional coverage for edge cases, error conditions,
and integration scenarios not covered in the main test file.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock
import time

import pytest

from levelup.core.tickets import add_ticket, set_ticket_status, TicketStatus


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


class TestRunStatusCaseSensitivity:
    """Test that run status values are case-sensitive as expected."""

    def test_get_ticket_status_color_run_status_case_sensitive(self):
        """Run status should be case-sensitive (lowercase expected)."""
        from levelup.gui.resources import get_ticket_status_color

        # Uppercase should not match and should return default
        color = get_ticket_status_color("in progress", theme="dark", run_status="RUNNING")
        # Should return default in progress color, not blue
        assert color == "#E6A817"

        # Mixed case should not match
        color = get_ticket_status_color("in progress", theme="dark", run_status="Running")
        assert color == "#E6A817"

        # Lowercase should match
        color = get_ticket_status_color("in progress", theme="dark", run_status="running")
        assert color == "#4A90D9"

    def test_ticket_status_case_sensitive(self):
        """Ticket status should be case-sensitive (lowercase expected)."""
        from levelup.gui.resources import get_ticket_status_color

        # "In Progress" should not match
        color = get_ticket_status_color("In Progress", theme="dark", run_status="running")
        # Should return default color (not found), not blue
        assert color == "#CDD6F4"


class TestColorDistinguishability:
    """Test that colors are actually different and distinguishable."""

    def test_running_and_waiting_colors_are_different_dark_theme(self):
        """Running (blue) and waiting (yellow-orange) should be clearly different in dark theme."""
        from levelup.gui.resources import get_ticket_status_color

        running_color = get_ticket_status_color("in progress", theme="dark", run_status="running")
        waiting_color = get_ticket_status_color("in progress", theme="dark", run_status="waiting_for_input")

        # Should be different colors
        assert running_color != waiting_color

        # Blue vs yellow-orange should be significantly different
        # Convert hex to RGB and verify they're not similar
        def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        running_rgb = hex_to_rgb(running_color)
        waiting_rgb = hex_to_rgb(waiting_color)

        # Calculate color distance (should be substantial)
        distance = sum((a - b) ** 2 for a, b in zip(running_rgb, waiting_rgb)) ** 0.5
        # Colors should be at least 100 units apart in RGB space
        assert distance > 100, f"Colors too similar: {running_color} vs {waiting_color}"

    def test_running_and_waiting_colors_are_different_light_theme(self):
        """Running (blue) and waiting (orange) should be clearly different in light theme."""
        from levelup.gui.resources import get_ticket_status_color

        running_color = get_ticket_status_color("in progress", theme="light", run_status="running")
        waiting_color = get_ticket_status_color("in progress", theme="light", run_status="waiting_for_input")

        assert running_color != waiting_color

        def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        running_rgb = hex_to_rgb(running_color)
        waiting_rgb = hex_to_rgb(waiting_color)

        distance = sum((a - b) ** 2 for a, b in zip(running_rgb, waiting_rgb)) ** 0.5
        assert distance > 100

    def test_colors_meet_accessibility_contrast_requirements(self):
        """Colors should have sufficient contrast for accessibility."""
        from levelup.gui.resources import get_ticket_status_color

        def hex_to_luminance(hex_color: str) -> float:
            """Calculate relative luminance for WCAG contrast ratio."""
            hex_color = hex_color.lstrip("#")
            r, g, b = [int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4)]

            # Apply gamma correction
            def gamma_correct(c: float) -> float:
                if c <= 0.03928:
                    return c / 12.92
                return ((c + 0.055) / 1.055) ** 2.4

            r, g, b = gamma_correct(r), gamma_correct(g), gamma_correct(b)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        def contrast_ratio(lum1: float, lum2: float) -> float:
            """Calculate WCAG contrast ratio."""
            lighter = max(lum1, lum2)
            darker = min(lum1, lum2)
            return (lighter + 0.05) / (darker + 0.05)

        # Dark theme background approximation (dark gray/black)
        dark_bg_luminance = hex_to_luminance("#1E1E2E")

        # Test running color has sufficient contrast on dark background
        running_color_dark = get_ticket_status_color("in progress", theme="dark", run_status="running")
        running_luminance = hex_to_luminance(running_color_dark)
        running_contrast = contrast_ratio(running_luminance, dark_bg_luminance)

        # WCAG AA requires 4.5:1 for normal text
        assert running_contrast >= 4.5, f"Running color contrast {running_contrast:.2f} too low on dark background"

        # Test waiting color has sufficient contrast on dark background
        waiting_color_dark = get_ticket_status_color("in progress", theme="dark", run_status="waiting_for_input")
        waiting_luminance = hex_to_luminance(waiting_color_dark)
        waiting_contrast = contrast_ratio(waiting_luminance, dark_bg_luminance)
        assert waiting_contrast >= 4.5, f"Waiting color contrast {waiting_contrast:.2f} too low on dark background"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestSidebarMemoryManagement:
    """Test that the sidebar properly manages memory for run status maps."""

    def test_run_status_map_is_cleared_when_tickets_cleared(self):
        """When tickets are cleared, run status map should also be cleared."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        # Set tickets with run status
        tickets = [
            Ticket(number=1, title="Test", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {1: "running"}
        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Verify it was stored
        assert widget._run_status_map == {1: "running"}

        # Clear tickets
        widget.set_tickets([])

        # Run status map should be cleared
        assert widget._run_status_map == {}

    def test_run_status_map_is_replaced_not_merged(self):
        """New run status map should replace old one, not merge."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        tickets = [
            Ticket(number=1, title="Test 1", status=TicketStatus.IN_PROGRESS),
            Ticket(number=2, title="Test 2", status=TicketStatus.IN_PROGRESS),
        ]

        # First update with ticket 1 running
        widget.set_tickets(tickets, run_status_map={1: "running"})
        assert widget._run_status_map == {1: "running"}

        # Second update with ticket 2 running (ticket 1 no longer running)
        widget.set_tickets(tickets, run_status_map={2: "waiting_for_input"})
        # Should only have ticket 2, not both
        assert widget._run_status_map == {2: "waiting_for_input"}

    def test_run_status_map_survives_multiple_theme_changes(self):
        """Run status map should persist through multiple rapid theme changes."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Running", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {1: "running"}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Rapid theme changes
        for _ in range(5):
            widget.update_theme("light")
            widget.update_theme("dark")

        # Run status should still be preserved
        item = widget._list.item(0)
        assert item.foreground().color().name().upper() == "#4A90D9"  # Dark blue for running


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestSidebarPerformance:
    """Test sidebar performance with large datasets."""

    def test_set_tickets_with_many_tickets(self):
        """Should handle large number of tickets efficiently."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        # Create 1000 tickets
        tickets = [
            Ticket(number=i, title=f"Ticket {i}", status=TicketStatus.IN_PROGRESS)
            for i in range(1, 1001)
        ]

        # Create run status map for every other ticket
        run_status_map = {
            i: "running" if i % 2 == 0 else "waiting_for_input"
            for i in range(1, 1001)
        }

        # Should complete quickly (under 1 second)
        start = time.time()
        widget.set_tickets(tickets, run_status_map=run_status_map)
        elapsed = time.time() - start

        assert elapsed < 1.0, f"set_tickets took {elapsed:.2f}s, expected < 1.0s"

        # Verify correct count
        assert widget._list.count() == 1000

        # Spot check some colors
        assert widget._list.item(1).foreground().color().name().upper() == "#4A90D9"  # Even: running
        assert widget._list.item(2).foreground().color().name().upper() == "#E6A817"  # Odd: waiting

    def test_update_theme_with_many_tickets(self):
        """Theme update should be efficient with many tickets."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        tickets = [
            Ticket(number=i, title=f"Ticket {i}", status=TicketStatus.IN_PROGRESS)
            for i in range(1, 501)
        ]
        run_status_map = {i: "running" for i in range(1, 501)}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Theme change should be quick
        start = time.time()
        widget.update_theme("light")
        elapsed = time.time() - start

        assert elapsed < 0.5, f"update_theme took {elapsed:.2f}s, expected < 0.5s"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestMainWindowIntegration:
    """Integration tests for MainWindow with real StateManager."""

    def test_refresh_tickets_with_real_state_manager_and_runs(self, tmp_path):
        """Test _refresh_tickets with actual StateManager and run records."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus

        # Create real state manager with DB
        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        # Create project with tickets
        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Running ticket")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)
        add_ticket(project_path, "Waiting ticket")
        set_ticket_status(project_path, 2, TicketStatus.IN_PROGRESS)
        add_ticket(project_path, "No run ticket")
        set_ticket_status(project_path, 3, TicketStatus.IN_PROGRESS)

        # Create real runs in the database
        ctx1 = PipelineContext(
            run_id="run1",
            task=TaskInput(title="Task 1"),
            project_path=str(project_path),
            ticket_number=1
        )
        ctx1.status = PipelineStatus.RUNNING
        state_manager.register_run(ctx1)
        state_manager.update_run(ctx1)

        ctx2 = PipelineContext(
            run_id="run2",
            task=TaskInput(title="Task 2"),
            project_path=str(project_path),
            ticket_number=2
        )
        ctx2.status = PipelineStatus.WAITING_FOR_INPUT
        state_manager.register_run(ctx2)
        state_manager.update_run(ctx2)

        # Create window
        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Trigger refresh which should load runs from DB
        window._refresh()

        # Verify sidebar colors
        item1 = window._sidebar._list.item(0)
        item2 = window._sidebar._list.item(1)
        item3 = window._sidebar._list.item(2)

        # Ticket 1: running - should be blue
        assert item1.foreground().color().name().upper() == "#4A90D9"

        # Ticket 2: waiting_for_input - should be yellow-orange
        assert item2.foreground().color().name().upper() == "#E6A817"

        # Ticket 3: no run - should be default yellow-orange
        assert item3.foreground().color().name().upper() == "#E6A817"

    def test_refresh_tickets_filters_completed_runs(self, tmp_path):
        """Completed runs should not affect ticket colors."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Ticket 1")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)
        add_ticket(project_path, "Ticket 2")
        set_ticket_status(project_path, 2, TicketStatus.IN_PROGRESS)

        # Create running run for ticket 1
        ctx1 = PipelineContext(
            run_id="run1",
            task=TaskInput(title="Task 1"),
            project_path=str(project_path),
            ticket_number=1
        )
        ctx1.status = PipelineStatus.RUNNING
        state_manager.register_run(ctx1)
        state_manager.update_run(ctx1)

        # Create completed run for ticket 2 (should not affect color)
        ctx2 = PipelineContext(
            run_id="run2",
            task=TaskInput(title="Task 2"),
            project_path=str(project_path),
            ticket_number=2
        )
        ctx2.status = PipelineStatus.COMPLETED
        state_manager.register_run(ctx2)
        state_manager.update_run(ctx2)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        window._refresh()

        # Ticket 1 should be blue (running)
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#4A90D9"

        # Ticket 2 should be default yellow-orange (completed run doesn't count)
        assert window._sidebar._list.item(1).foreground().color().name().upper() == "#E6A817"


class TestNullAndNoneHandling:
    """Test handling of None and null values in various scenarios."""

    def test_get_ticket_status_color_with_none_theme(self):
        """None theme should fall back to dark theme."""
        from levelup.gui.resources import get_ticket_status_color

        # Should not raise
        color = get_ticket_status_color("in progress", theme=None, run_status="running")
        # Should return dark theme blue
        assert color == "#4A90D9"

    def test_get_ticket_status_color_with_empty_status(self):
        """Empty string status should return default."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("", theme="dark", run_status="running")
        # Should return default color (not blue)
        assert color == "#CDD6F4"

    @pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
    def test_set_tickets_with_zero_ticket_number(self):
        """Tickets with zero or negative numbers should be handled gracefully."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        # Create ticket with zero number (edge case)
        ticket = Ticket(number=0, title="Zero number", status=TicketStatus.IN_PROGRESS)

        # Should not raise
        widget.set_tickets([ticket], run_status_map={1: "running"})

        # Should have one item
        assert widget._list.count() == 1


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestConcurrentUpdates:
    """Test behavior when tickets and run statuses are updated concurrently."""

    def test_rapid_run_status_updates(self):
        """Rapid updates to run status should maintain consistency."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Test", status=TicketStatus.IN_PROGRESS),
        ]

        # Rapidly change run status
        statuses = ["running", "waiting_for_input", "running", "waiting_for_input", "running"]
        expected_colors = ["#4A90D9", "#E6A817", "#4A90D9", "#E6A817", "#4A90D9"]

        for status, expected in zip(statuses, expected_colors):
            widget.set_tickets(tickets, run_status_map={1: status})
            item = widget._list.item(0)
            assert item.foreground().color().name().upper() == expected

    def test_ticket_list_update_while_run_status_changes(self):
        """Updating ticket list while run statuses change should work correctly."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        # Initial state: 2 tickets, 1 running
        tickets_v1 = [
            Ticket(number=1, title="Test 1", status=TicketStatus.IN_PROGRESS),
            Ticket(number=2, title="Test 2", status=TicketStatus.IN_PROGRESS),
        ]
        widget.set_tickets(tickets_v1, run_status_map={1: "running"})

        # Update: 3 tickets, different one running
        tickets_v2 = [
            Ticket(number=1, title="Test 1", status=TicketStatus.IN_PROGRESS),
            Ticket(number=2, title="Test 2", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Test 3", status=TicketStatus.IN_PROGRESS),
        ]
        widget.set_tickets(tickets_v2, run_status_map={2: "waiting_for_input"})

        # Verify final state
        assert widget._list.count() == 3
        assert widget._list.item(0).foreground().color().name().upper() == "#E6A817"  # No run
        assert widget._list.item(1).foreground().color().name().upper() == "#E6A817"  # Waiting
        assert widget._list.item(2).foreground().color().name().upper() == "#E6A817"  # No run


class TestColorValueValidation:
    """Test that color values are valid hex colors."""

    def test_all_run_status_colors_are_valid_hex(self):
        """All run status colors should be valid 7-character hex colors."""
        from levelup.gui.resources import get_ticket_status_color

        statuses = ["running", "waiting_for_input"]
        themes = ["dark", "light"]

        for status in statuses:
            for theme in themes:
                color = get_ticket_status_color("in progress", theme=theme, run_status=status)
                assert color.startswith("#"), f"Color {color} doesn't start with #"
                assert len(color) == 7, f"Color {color} is not 7 characters"
                # Verify it's valid hex
                try:
                    int(color[1:], 16)
                except ValueError:
                    pytest.fail(f"Color {color} is not valid hex")

    def test_all_ticket_status_colors_are_valid_hex(self):
        """All ticket status colors should be valid 7-character hex colors."""
        from levelup.gui.resources import get_ticket_status_color

        statuses = ["pending", "in progress", "done", "merged"]
        themes = ["dark", "light"]

        for status in statuses:
            for theme in themes:
                color = get_ticket_status_color(status, theme=theme)
                assert color.startswith("#"), f"Color {color} doesn't start with #"
                assert len(color) == 7, f"Color {color} is not 7 characters"
                try:
                    int(color[1:], 16)
                except ValueError:
                    pytest.fail(f"Color {color} is not valid hex")


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestSelectionPreservation:
    """Test that selection is properly preserved across updates."""

    def test_selection_preserved_when_run_status_changes(self):
        """Selection should persist when only run status changes."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Ticket 1", status=TicketStatus.IN_PROGRESS),
            Ticket(number=2, title="Ticket 2", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Ticket 3", status=TicketStatus.IN_PROGRESS),
        ]

        # Set tickets and select middle one
        widget.set_tickets(tickets)
        widget._list.setCurrentRow(1)

        # Update run status for first ticket
        widget.set_tickets(tickets, run_status_map={1: "running"})

        # Selection should still be on ticket 2
        assert widget._list.currentRow() == 1

    def test_selection_preserved_when_theme_changes(self):
        """Selection should persist through theme change."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Ticket 1", status=TicketStatus.IN_PROGRESS),
            Ticket(number=2, title="Ticket 2", status=TicketStatus.IN_PROGRESS),
        ]

        widget.set_tickets(tickets, run_status_map={1: "running"})
        widget._list.setCurrentRow(0)

        # Change theme
        widget.update_theme("light")

        # Selection should be preserved
        assert widget._list.currentRow() == 0

    def test_selection_adjusted_when_ticket_removed(self):
        """Selection should adjust appropriately when selected ticket is removed."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets_v1 = [
            Ticket(number=1, title="Ticket 1", status=TicketStatus.IN_PROGRESS),
            Ticket(number=2, title="Ticket 2", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Ticket 3", status=TicketStatus.IN_PROGRESS),
        ]

        widget.set_tickets(tickets_v1)
        widget._list.setCurrentRow(1)  # Select ticket 2

        # Remove ticket 2
        tickets_v2 = [
            Ticket(number=1, title="Ticket 1", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Ticket 3", status=TicketStatus.IN_PROGRESS),
        ]

        widget.set_tickets(tickets_v2)

        # Selection should be cleared since ticket 2 is gone
        assert widget._list.currentRow() == -1
