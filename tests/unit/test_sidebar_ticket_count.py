"""Unit tests for accurate ticket count display in sidebar when filtering.

This test suite covers the requirement that the sidebar should show
accurate ticket count when merged tickets are hidden or shown.

Requirements:
- Ticket count reflects the number of visible tickets
- Ticket count updates when filter state changes
- Ticket count is accurate with different ticket status combinations
"""

from __future__ import annotations

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


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestSidebarTicketCount:
    """Test accurate ticket count display in sidebar."""

    def test_count_excludes_merged_by_default(self):
        """Ticket count should exclude merged tickets when filter is off."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="In progress", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Done", status=TicketStatus.DONE),
            Ticket(number=4, title="Merged", status=TicketStatus.MERGED),
            Ticket(number=5, title="Merged 2", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        # Count should be 3 (excluding 2 merged tickets)
        assert widget._list.count() == 3

    def test_count_includes_merged_when_filter_on(self):
        """Ticket count should include merged tickets when filter is on."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        # Show merged tickets
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        widget.set_tickets(tickets)

        # Count should be 2 (including merged)
        assert widget._list.count() == 2

    def test_count_updates_when_toggling_filter(self):
        """Ticket count should update immediately when toggling filter."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged 1", status=TicketStatus.MERGED),
            Ticket(number=3, title="Merged 2", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        # Initially 1 ticket (merged hidden)
        assert widget._list.count() == 1

        # Show merged
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)

        # Now 3 tickets
        assert widget._list.count() == 3

        # Hide merged again
        checkbox.setChecked(False)

        # Back to 1 ticket
        assert widget._list.count() == 1

    def test_count_zero_when_all_tickets_merged_and_hidden(self):
        """Ticket count should be zero when all tickets are merged and filter is off."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Merged 1", status=TicketStatus.MERGED),
            Ticket(number=2, title="Merged 2", status=TicketStatus.MERGED),
            Ticket(number=3, title="Merged 3", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        # Count should be 0 (all merged and hidden)
        assert widget._list.count() == 0

    def test_count_matches_total_when_no_merged_tickets(self):
        """Ticket count should match total when there are no merged tickets."""
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

        # Count should be 3 (all visible)
        assert widget._list.count() == 3

    def test_count_accurate_with_mixed_statuses(self):
        """Ticket count should be accurate with various ticket status combinations."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending 1", status=TicketStatus.PENDING),
            Ticket(number=2, title="Pending 2", status=TicketStatus.PENDING),
            Ticket(number=3, title="In progress", status=TicketStatus.IN_PROGRESS),
            Ticket(number=4, title="Done 1", status=TicketStatus.DONE),
            Ticket(number=5, title="Done 2", status=TicketStatus.DONE),
            Ticket(number=6, title="Merged 1", status=TicketStatus.MERGED),
            Ticket(number=7, title="Merged 2", status=TicketStatus.MERGED),
            Ticket(number=8, title="Merged 3", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        # Count should be 5 (2 pending + 1 in progress + 2 done, excluding 3 merged)
        assert widget._list.count() == 5

    def test_count_updates_on_ticket_list_refresh(self):
        """Ticket count should update when ticket list is refreshed."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets1 = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
        ]

        widget.set_tickets(tickets1)
        assert widget._list.count() == 1

        # Refresh with more tickets
        tickets2 = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Done", status=TicketStatus.DONE),
            Ticket(number=3, title="Merged", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets2)

        # Count should be 2 (excluding merged)
        assert widget._list.count() == 2

    def test_count_consistent_after_multiple_updates(self):
        """Ticket count should remain consistent after multiple ticket updates."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()

        # First update
        tickets1 = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]
        widget.set_tickets(tickets1)
        assert widget._list.count() == 1

        # Second update
        tickets2 = [
            Ticket(number=1, title="Done", status=TicketStatus.DONE),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]
        widget.set_tickets(tickets2)
        assert widget._list.count() == 1

        # Third update
        tickets3 = [
            Ticket(number=1, title="Done", status=TicketStatus.DONE),
            Ticket(number=2, title="Merged 1", status=TicketStatus.MERGED),
            Ticket(number=3, title="Merged 2", status=TicketStatus.MERGED),
        ]
        widget.set_tickets(tickets3)
        assert widget._list.count() == 1


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestTicketCountWithRunStatus:
    """Test ticket count accuracy with run status mapping."""

    def test_count_unchanged_by_run_status(self):
        """Run status should not affect ticket count."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Running", status=TicketStatus.IN_PROGRESS),
            Ticket(number=2, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=3, title="Merged", status=TicketStatus.MERGED),
        ]

        run_status_map = {1: "running"}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Count should be 2 (merged hidden, run status doesn't affect count)
        assert widget._list.count() == 2

    def test_count_with_merged_ticket_having_run_status(self):
        """Merged ticket with run status should still be excluded from count."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        # Merged ticket has a run status (shouldn't affect filtering)
        run_status_map = {2: "running"}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Count should be 1 (merged hidden regardless of run status)
        assert widget._list.count() == 1


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestTicketCountEdgeCases:
    """Test edge cases for ticket count accuracy."""

    def test_count_zero_with_empty_ticket_list(self):
        """Count should be zero with empty ticket list."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        widget = TicketSidebarWidget()
        widget.set_tickets([])

        assert widget._list.count() == 0

    def test_count_accurate_after_theme_change(self):
        """Ticket count should remain accurate after theme change."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Merged", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)
        assert widget._list.count() == 1

        # Change theme
        widget.update_theme("light")

        # Count should remain the same
        assert widget._list.count() == 1

    def test_count_with_single_merged_ticket(self):
        """Count should be zero when only ticket is merged."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Merged", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        assert widget._list.count() == 0

    def test_count_with_many_tickets(self):
        """Count should be accurate with large number of tickets."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()

        # Create 50 pending tickets and 50 merged tickets
        tickets = []
        for i in range(50):
            tickets.append(Ticket(number=i, title=f"Pending {i}", status=TicketStatus.PENDING))
        for i in range(50, 100):
            tickets.append(Ticket(number=i, title=f"Merged {i}", status=TicketStatus.MERGED))

        widget.set_tickets(tickets)

        # Count should be 50 (only pending tickets visible)
        assert widget._list.count() == 50

    def test_count_reflects_actual_visible_items(self):
        """Count should exactly match the number of visible items in the list."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = TicketSidebarWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Done", status=TicketStatus.DONE),
            Ticket(number=3, title="Merged", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        # Count visible items manually
        visible_count = 0
        for i in range(widget._list.count()):
            if widget._list.item(i) is not None:
                visible_count += 1

        # Count should match visible items
        assert widget._list.count() == visible_count
        assert visible_count == 2  # Pending and Done (Merged hidden)
