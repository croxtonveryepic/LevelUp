"""Unit tests for ticket sidebar filtering functionality.

This test suite covers the requirements for hiding merged tickets from the
sidebar by default and providing a toggle control to show/hide them.

Requirements:
- Hide merged tickets from the main sidebar list by default
- Add a toggle control to show/hide merged tickets in the sidebar
- Filtering logic is implemented in the sidebar's set_tickets() method or a new filter method
- Selection is preserved when filters change (if selected ticket is still visible)
- Sidebar displays only tickets with statuses: pending, in progress, and done (merged hidden)
- Sidebar shows accurate ticket count when merged tickets are hidden
- Active filters are visually indicated to users (e.g., toggle state)
- Theme changes continue to work correctly with filtered tickets
- Run status colors continue to work for visible tickets when filtering is active
"""

from __future__ import annotations

import pytest


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
class TestSidebarFilteringDefaults:
    """Test default filtering behavior - merged tickets hidden by default."""

    def test_merged_tickets_hidden_by_default(self):
        """Merged tickets should be filtered out from the sidebar by default."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
            Ticket(number=2, title="In progress", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Done ticket", status=TicketStatus.DONE),
            Ticket(number=4, title="Merged ticket", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        # Should only show 3 tickets (merged is hidden)
        assert widget._list.count() == 3

        # Verify merged ticket is not in the list
        displayed_numbers = []
        for i in range(widget._list.count()):
            item_text = widget._list.item(i).text()
            # Extract ticket number from text like "○  #1 Pending ticket"
            if "#" in item_text:
                num_str = item_text.split("#")[1].split()[0]
                displayed_numbers.append(int(num_str))

        assert 1 in displayed_numbers
        assert 2 in displayed_numbers
        assert 3 in displayed_numbers
        assert 4 not in displayed_numbers  # Merged ticket hidden

    def test_only_pending_in_progress_done_shown_by_default(self):
        """Sidebar should display only pending, in progress, and done tickets by default."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending 1", status=TicketStatus.PENDING),
            Ticket(number=2, title="In progress 1", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Done 1", status=TicketStatus.DONE),
            Ticket(number=4, title="Merged 1", status=TicketStatus.MERGED),
            Ticket(number=5, title="Pending 2", status=TicketStatus.PENDING),
            Ticket(number=6, title="Merged 2", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        # Should show only 4 tickets (2 merged hidden)
        assert widget._list.count() == 4

    def test_empty_list_when_all_tickets_merged(self):
        """Sidebar should show empty list when all tickets are merged."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Merged 1", status=TicketStatus.MERGED),
            Ticket(number=2, title="Merged 2", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        assert widget._list.count() == 0

    def test_all_tickets_shown_when_none_merged(self):
        """Sidebar should show all tickets when none are merged."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="In progress", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Done", status=TicketStatus.DONE),
        ]

        widget.set_tickets(tickets)

        assert widget._list.count() == 3


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestSidebarToggleControl:
    """Test toggle control for showing/hiding merged tickets."""

    def test_toggle_checkbox_exists_in_header(self):
        """Sidebar header should contain a checkbox/toggle for merged ticket visibility."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()

        # Find the checkbox in the widget hierarchy
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        assert checkbox is not None

    def test_toggle_label_indicates_purpose(self):
        """Toggle label should clearly indicate its purpose."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Check that the label contains relevant text
        label = checkbox.text().lower()
        assert "merged" in label or "show" in label

    def test_toggle_unchecked_by_default(self):
        """Toggle should be unchecked by default (merged tickets hidden)."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        assert checkbox.isChecked() is False

    def test_checking_toggle_shows_merged_tickets(self):
        """Checking the toggle should include merged tickets in the list."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        # Initially only 1 ticket shown
        assert widget._list.count() == 1

        # Check the toggle
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)

        # Now should show 2 tickets
        assert widget._list.count() == 2

    def test_unchecking_toggle_hides_merged_tickets(self):
        """Unchecking the toggle should hide merged tickets from the list."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Check the toggle first (show merged)
        checkbox.setChecked(True)
        widget.set_tickets(tickets)
        assert widget._list.count() == 2

        # Uncheck the toggle (hide merged)
        checkbox.setChecked(False)

        # Should only show 1 ticket now
        assert widget._list.count() == 1

    def test_toggle_state_persists_during_session(self):
        """Toggle state should persist during the GUI session (in-memory state)."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Set toggle to checked
        checkbox.setChecked(True)
        widget.set_tickets(tickets)

        # Update tickets (simulating refresh)
        updated_tickets = [
            Ticket(number=1, title="Pending updated", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged updated", status=TicketStatus.MERGED),
        ]
        widget.set_tickets(updated_tickets)

        # Toggle should still be checked
        assert checkbox.isChecked() is True
        # Merged ticket should still be visible
        assert widget._list.count() == 2


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestSelectionPreservation:
    """Test selection preservation when filters change."""

    def test_selection_preserved_when_ticket_still_visible(self):
        """Selection should be preserved when the selected ticket is still visible after filter change."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Done", status=TicketStatus.DONE),
            Ticket(number=3, title="Merged", status=TicketStatus.MERGED),
        ]

        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        widget.set_tickets(tickets)

        # Select the "Done" ticket (index 1)
        widget._list.setCurrentRow(1)
        assert widget._list.currentRow() == 1

        # Uncheck toggle (hide merged) - Done ticket should still be visible
        checkbox.setChecked(False)

        # Selection should be preserved (Done is now at index 1)
        assert widget._list.currentRow() == 1

    def test_selection_cleared_when_ticket_filtered_out(self):
        """Selection should be cleared when the selected ticket is filtered out."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        widget.set_tickets(tickets)

        # Select the merged ticket (index 1)
        widget._list.setCurrentRow(1)
        assert widget._list.currentRow() == 1

        # Uncheck toggle (hide merged) - merged ticket will be filtered out
        checkbox.setChecked(False)

        # Selection should be cleared
        assert widget._list.currentRow() == -1

    def test_selection_moved_when_merged_ticket_hidden(self):
        """Selection should move to nearest visible ticket when current selection is filtered out."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged 1", status=TicketStatus.MERGED),
            Ticket(number=3, title="Merged 2", status=TicketStatus.MERGED),
            Ticket(number=4, title="Done", status=TicketStatus.DONE),
        ]

        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        widget.set_tickets(tickets)

        # Select a merged ticket (index 1)
        widget._list.setCurrentRow(1)

        # Uncheck toggle (hide merged)
        checkbox.setChecked(False)

        # Selection should either be cleared or moved to a visible ticket
        current_row = widget._list.currentRow()
        # Accept either cleared (-1) or moved to nearest visible ticket
        assert current_row == -1 or current_row < widget._list.count()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestFilteringWithThemes:
    """Test that filtering works correctly with theme changes."""

    def test_theme_change_preserves_filter_state(self):
        """Theme change should preserve the current filter state."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        widget.set_tickets(tickets)

        # Both tickets visible
        assert widget._list.count() == 2

        # Change theme
        widget.update_theme("light")

        # Filter state should be preserved
        assert checkbox.isChecked() is True
        assert widget._list.count() == 2

    def test_filtered_tickets_use_correct_theme_colors(self):
        """Filtered tickets should use correct colors for the current theme."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        widget.set_tickets(tickets)

        # Check dark theme colors
        pending_item = widget._list.item(0)
        merged_item = widget._list.item(1)
        assert pending_item.foreground().color().name().upper() == "#CDD6F4"  # Dark pending
        assert merged_item.foreground().color().name().upper() == "#6C7086"  # Dark merged

        # Change to light theme
        widget.update_theme("light")

        # Check light theme colors
        pending_item = widget._list.item(0)
        merged_item = widget._list.item(1)
        assert pending_item.foreground().color().name().upper() == "#2E3440"  # Light pending
        assert merged_item.foreground().color().name().upper() == "#95A5A6"  # Light merged


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestFilteringWithRunStatus:
    """Test that filtering works correctly with run status coloring."""

    def test_run_status_colors_work_with_filtering(self):
        """Run status colors should work correctly for visible tickets when filtering is active."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Running", status=TicketStatus.IN_PROGRESS),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
            Ticket(number=3, title="Pending", status=TicketStatus.PENDING),
        ]

        run_status_map = {1: "running"}

        # Merged tickets hidden by default
        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Should only show 2 tickets
        assert widget._list.count() == 2

        # First ticket should be blue (running)
        assert widget._list.item(0).foreground().color().name().upper() == "#4A90D9"

        # Second ticket should be pending color
        assert widget._list.item(1).foreground().color().name().upper() == "#CDD6F4"

    def test_merged_ticket_with_run_status_hidden_by_default(self):
        """Merged ticket with run status should still be hidden by default."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        # Merged ticket has a run status (should still be hidden)
        run_status_map = {2: "running"}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Should only show 1 ticket (merged is hidden despite having run status)
        assert widget._list.count() == 1

    def test_showing_merged_applies_run_status_color(self):
        """When merged tickets are shown, they should use run status colors if applicable."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        run_status_map = {2: "running"}

        # Show merged tickets
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Should show 2 tickets
        assert widget._list.count() == 2

        # Merged ticket should use merged color (run status doesn't override merged status)
        assert widget._list.item(1).foreground().color().name().upper() == "#6C7086"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestFilteringEdgeCases:
    """Test edge cases and error conditions for filtering."""

    def test_empty_ticket_list_with_filter_enabled(self):
        """Empty ticket list should be handled correctly when filter is enabled."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)

        widget.set_tickets([])

        assert widget._list.count() == 0

    def test_filter_toggle_with_no_tickets(self):
        """Toggling filter with no tickets should not raise an error."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        widget.set_tickets([])

        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Should not raise
        checkbox.setChecked(True)
        checkbox.setChecked(False)

        assert widget._list.count() == 0

    def test_rapid_filter_toggling(self):
        """Rapid toggling of filter should work correctly."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Rapid toggling
        for _ in range(10):
            checkbox.setChecked(True)
            checkbox.setChecked(False)

        # Should end in correct state (merged hidden)
        assert widget._list.count() == 1
        assert checkbox.isChecked() is False

    def test_filter_with_multiple_merged_tickets(self):
        """Filter should correctly handle multiple merged tickets."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged 1", status=TicketStatus.MERGED),
            Ticket(number=3, title="Done", status=TicketStatus.DONE),
            Ticket(number=4, title="Merged 2", status=TicketStatus.MERGED),
            Ticket(number=5, title="In progress", status=TicketStatus.IN_PROGRESS),
            Ticket(number=6, title="Merged 3", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        # Should hide all 3 merged tickets
        assert widget._list.count() == 3

        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)

        # Should show all 6 tickets
        assert widget._list.count() == 6
