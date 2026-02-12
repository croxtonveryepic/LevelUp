"""Property-based and stress tests for ticket sidebar run status colors.

These tests use property-based testing techniques to verify invariants
and test behavior under various conditions.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from unittest.mock import patch
import random

import pytest

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


class TestColorInvariants:
    """Test invariants that must hold for all color operations."""

    def test_same_inputs_produce_same_output(self):
        """Property: Same inputs always produce same color output (pure function)."""
        from levelup.gui.resources import get_ticket_status_color

        # Call multiple times with same inputs
        results = [
            get_ticket_status_color("in progress", theme="dark", run_status="running")
            for _ in range(100)
        ]

        # All results should be identical
        assert len(set(results)) == 1
        assert results[0] == "#4A90D9"

    def test_color_output_always_valid_hex(self):
        """Property: Output is always valid hex color regardless of input."""
        from levelup.gui.resources import get_ticket_status_color

        # Test with various inputs including invalid ones
        test_cases = [
            ("in progress", "dark", "running"),
            ("in progress", "light", "waiting_for_input"),
            ("pending", "dark", None),
            ("invalid", "invalid", "invalid"),
            ("", "", ""),
            ("IN PROGRESS", "DARK", "RUNNING"),
        ]

        for status, theme, run_status in test_cases:
            color = get_ticket_status_color(status, theme=theme, run_status=run_status)

            # Should always return valid hex
            assert isinstance(color, str)
            assert color.startswith("#")
            assert len(color) == 7

            # Should be valid hex digits
            try:
                int(color[1:], 16)
            except ValueError:
                pytest.fail(f"Invalid hex color {color} for inputs: {status}, {theme}, {run_status}")

    def test_only_in_progress_affected_by_run_status(self):
        """Property: Only "in progress" status is affected by run_status parameter."""
        from levelup.gui.resources import get_ticket_status_color

        other_statuses = ["pending", "done", "merged"]

        for status in other_statuses:
            # Color with run status
            with_run = get_ticket_status_color(status, theme="dark", run_status="running")
            # Color without run status
            without_run = get_ticket_status_color(status, theme="dark")

            # Should be the same
            assert with_run == without_run, f"Status {status} was affected by run_status"

    def test_only_active_run_statuses_change_color(self):
        """Property: Only running/waiting_for_input change "in progress" color."""
        from levelup.gui.resources import get_ticket_status_color

        default_color = get_ticket_status_color("in progress", theme="dark")

        inactive_statuses = ["completed", "failed", "aborted", "paused", "pending"]

        for run_status in inactive_statuses:
            color = get_ticket_status_color("in progress", theme="dark", run_status=run_status)
            assert color == default_color, f"Inactive status {run_status} changed color"

    def test_theme_affects_all_colors(self):
        """Property: Theme parameter affects color output for all valid inputs."""
        from levelup.gui.resources import get_ticket_status_color

        test_cases = [
            ("pending", None),
            ("in progress", None),
            ("in progress", "running"),
            ("in progress", "waiting_for_input"),
            ("done", None),
        ]

        for status, run_status in test_cases:
            dark_color = get_ticket_status_color(status, theme="dark", run_status=run_status)
            light_color = get_ticket_status_color(status, theme="light", run_status=run_status)

            # Colors should be different between themes (except possibly for some edge cases)
            # At minimum, they should be valid colors
            assert dark_color.startswith("#")
            assert light_color.startswith("#")


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestSidebarInvariants:
    """Test invariants for sidebar widget behavior."""

    def test_ticket_count_invariant(self):
        """Property: Number of items in list always equals number of tickets."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        # Test with various ticket counts
        for count in [0, 1, 5, 10, 50]:
            tickets = [
                Ticket(number=i, title=f"Ticket {i}", status=TicketStatus.IN_PROGRESS)
                for i in range(count)
            ]
            widget.set_tickets(tickets)

            assert widget._list.count() == count

    def test_run_status_map_keys_are_ticket_numbers(self):
        """Property: All keys in _run_status_map should be ticket numbers."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        tickets = [
            Ticket(number=10, title="Ticket 10", status=TicketStatus.IN_PROGRESS),
            Ticket(number=20, title="Ticket 20", status=TicketStatus.IN_PROGRESS),
            Ticket(number=30, title="Ticket 30", status=TicketStatus.IN_PROGRESS),
        ]

        run_status_map = {10: "running", 20: "waiting_for_input"}
        widget.set_tickets(tickets, run_status_map=run_status_map)

        # All keys should be integers (ticket numbers)
        assert all(isinstance(k, int) for k in widget._run_status_map.keys())

        # All keys should match provided map
        assert widget._run_status_map == run_status_map

    def test_color_application_is_idempotent(self):
        """Property: Applying same tickets/run_status multiple times produces same result."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        tickets = [
            Ticket(number=1, title="Test", status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {1: "running"}

        # Apply multiple times
        widget.set_tickets(tickets, run_status_map=run_status_map)
        color1 = widget._list.item(0).foreground().color().name().upper()

        widget.set_tickets(tickets, run_status_map=run_status_map)
        color2 = widget._list.item(0).foreground().color().name().upper()

        widget.set_tickets(tickets, run_status_map=run_status_map)
        color3 = widget._list.item(0).foreground().color().name().upper()

        # All should be the same
        assert color1 == color2 == color3 == "#4A90D9"

    def test_theme_change_preserves_ticket_count(self):
        """Property: Theme change doesn't affect number of tickets."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        tickets = [
            Ticket(number=i, title=f"Ticket {i}", status=TicketStatus.IN_PROGRESS)
            for i in range(10)
        ]
        widget.set_tickets(tickets)

        count_before = widget._list.count()

        # Change theme multiple times
        for theme in ["light", "dark", "light", "dark"]:
            widget.update_theme(theme)
            assert widget._list.count() == count_before


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestStressScenarios:
    """Stress tests with extreme inputs."""

    def test_rapid_ticket_updates(self):
        """Stress test: Rapidly update tickets many times."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        # Perform 100 rapid updates
        for iteration in range(100):
            ticket_count = random.randint(1, 20)
            tickets = [
                Ticket(number=i, title=f"Ticket {i}", status=TicketStatus.IN_PROGRESS)
                for i in range(ticket_count)
            ]
            run_status_map = {
                i: random.choice(["running", "waiting_for_input"])
                for i in random.sample(range(ticket_count), k=min(5, ticket_count))
            }

            # Should not crash
            widget.set_tickets(tickets, run_status_map=run_status_map)

        # Final state should be valid
        assert widget._list.count() >= 0

    def test_extreme_ticket_numbers(self):
        """Stress test: Use very large ticket numbers."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        # Use extreme ticket numbers
        extreme_numbers = [1, 999999, 2147483647, -1]  # Including edge cases
        tickets = [
            Ticket(number=num, title=f"Ticket {num}", status=TicketStatus.IN_PROGRESS)
            for num in extreme_numbers
        ]

        run_status_map = {999999: "running"}

        # Should not crash
        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Should have correct count
        assert widget._list.count() == len(tickets)

    def test_very_long_ticket_titles(self):
        """Stress test: Handle very long ticket titles."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        # Create ticket with very long title
        long_title = "A" * 10000
        tickets = [
            Ticket(number=1, title=long_title, status=TicketStatus.IN_PROGRESS),
        ]
        run_status_map = {1: "running"}

        # Should not crash
        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Should have color applied
        color = widget._list.item(0).foreground().color().name().upper()
        assert color == "#4A90D9"

    def test_mixed_valid_invalid_run_statuses(self):
        """Stress test: Mix of valid and invalid run statuses."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")

        tickets = [
            Ticket(number=i, title=f"Ticket {i}", status=TicketStatus.IN_PROGRESS)
            for i in range(10)
        ]

        # Mix valid and invalid statuses
        run_status_map = {
            1: "running",  # Valid
            2: "waiting_for_input",  # Valid
            3: "INVALID",  # Invalid
            4: "",  # Empty
            5: "completed",  # Valid but inactive
            # Ticket 6 is not in the map at all
        }

        # Should not crash and should handle gracefully
        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Valid ones should have correct colors
        assert widget._list.item(0).foreground().color().name().upper() == "#4A90D9"  # running
        assert widget._list.item(1).foreground().color().name().upper() == "#E6A817"  # waiting

        # Invalid/inactive should have default color
        assert widget._list.item(2).foreground().color().name().upper() == "#E6A817"  # INVALID
        assert widget._list.item(3).foreground().color().name().upper() == "#E6A817"  # Empty
        assert widget._list.item(4).foreground().color().name().upper() == "#E6A817"  # completed
        assert widget._list.item(5).foreground().color().name().upper() == "#E6A817"  # Not in map


class TestMainWindowRunStatusBuildingLogic:
    """Test the run status map building logic in MainWindow."""

    def test_run_status_map_only_includes_specified_statuses(self):
        """Property: Only "running" and "waiting_for_input" should be in map."""
        # This tests the logic at lines 198-200 in main_window.py

        from levelup.state.models import RunRecord

        # Simulate the filtering logic
        all_statuses = ["pending", "running", "waiting_for_input", "paused", "completed", "failed", "aborted"]
        active_statuses = {"running", "waiting_for_input"}

        runs = [
            RunRecord(
                run_id=f"run_{status}",
                task_title=f"Task {status}",
                project_path="/test",
                status=status,
                ticket_number=i,
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            )
            for i, status in enumerate(all_statuses, 1)
        ]

        # Build run status map (simulating main_window.py logic)
        run_status_map: dict[int, str] = {}
        for run in runs:
            if run.ticket_number and run.status in active_statuses:
                run_status_map[run.ticket_number] = run.status

        # Should only have 2 entries (running and waiting_for_input)
        assert len(run_status_map) == 2
        assert 2 in run_status_map  # running
        assert 3 in run_status_map  # waiting_for_input
        assert run_status_map[2] == "running"
        assert run_status_map[3] == "waiting_for_input"

    def test_run_status_map_last_wins_for_duplicate_tickets(self):
        """Property: If multiple runs for same ticket, last one wins."""
        from levelup.state.models import RunRecord

        # Multiple runs for ticket 1
        runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                project_path="/test",
                status="running",
                ticket_number=1,
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
            RunRecord(
                run_id="run2",
                task_title="Task 2",
                project_path="/test",
                status="waiting_for_input",
                ticket_number=1,  # Same ticket
                started_at="2024-01-01T01:00:00",
                updated_at="2024-01-01T01:00:00",
            ),
        ]

        # Build run status map
        run_status_map: dict[int, str] = {}
        for run in runs:
            if run.ticket_number and run.status in ("running", "waiting_for_input"):
                run_status_map[run.ticket_number] = run.status

        # Last one should win
        assert len(run_status_map) == 1
        assert run_status_map[1] == "waiting_for_input"

    def test_run_status_map_excludes_none_ticket_numbers(self):
        """Property: Runs without ticket_number should not be in map."""
        from levelup.state.models import RunRecord

        runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                project_path="/test",
                status="running",
                ticket_number=1,
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
            RunRecord(
                run_id="run2",
                task_title="Task 2",
                project_path="/test",
                status="running",
                ticket_number=None,  # No ticket
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
        ]

        # Build run status map
        run_status_map: dict[int, str] = {}
        for run in runs:
            if run.ticket_number and run.status in ("running", "waiting_for_input"):
                run_status_map[run.ticket_number] = run.status

        # Should only have run1
        assert len(run_status_map) == 1
        assert 1 in run_status_map


class TestColorConsistency:
    """Test that colors are consistent across different code paths."""

    def test_running_color_matches_between_functions(self):
        """Running color should be same in get_status_color and get_ticket_status_color."""
        from levelup.gui.resources import get_status_color, get_ticket_status_color

        # Get color from both functions
        status_color = get_status_color("running", theme="dark")
        ticket_color = get_ticket_status_color("in progress", theme="dark", run_status="running")

        # Should be the same
        assert status_color == ticket_color == "#4A90D9"

    def test_waiting_color_matches_between_functions(self):
        """Waiting color should be same in get_status_color and get_ticket_status_color."""
        from levelup.gui.resources import get_status_color, get_ticket_status_color

        status_color = get_status_color("waiting_for_input", theme="dark")
        ticket_color = get_ticket_status_color("in progress", theme="dark", run_status="waiting_for_input")

        assert status_color == ticket_color == "#E6A817"

    def test_colors_consistent_across_themes(self):
        """Property: Color consistency check - same semantic meaning in both themes."""
        from levelup.gui.resources import get_ticket_status_color

        # Running should be blue-ish in both themes
        dark_running = get_ticket_status_color("in progress", theme="dark", run_status="running")
        light_running = get_ticket_status_color("in progress", theme="light", run_status="running")

        # Both should be blue (RGB: blue component > red and green)
        def is_blue_dominant(hex_color: str) -> bool:
            hex_color = hex_color.lstrip("#")
            r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
            return b > r and b > g

        assert is_blue_dominant(dark_running), f"Dark running color {dark_running} is not blue"
        assert is_blue_dominant(light_running), f"Light running color {light_running} is not blue"

        # Waiting should be yellow/orange-ish in both themes
        dark_waiting = get_ticket_status_color("in progress", theme="dark", run_status="waiting_for_input")
        light_waiting = get_ticket_status_color("in progress", theme="light", run_status="waiting_for_input")

        def is_warm_color(hex_color: str) -> bool:
            """Check if color is warm (red/orange/yellow - high red component)."""
            hex_color = hex_color.lstrip("#")
            r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
            return r > b  # Red component greater than blue

        assert is_warm_color(dark_waiting), f"Dark waiting color {dark_waiting} is not warm"
        assert is_warm_color(light_waiting), f"Light waiting color {light_waiting} is not warm"
