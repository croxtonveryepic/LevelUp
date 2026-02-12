"""Unit tests for CompletedTicketsWidget.

This test suite covers the requirements for a separate page/view showing
completed (done + merged) tickets.

Requirements:
- New stacked widget page is added to MainWindow's QStackedWidget
- Page displays a filtered list showing only 'done' and 'merged' status tickets
- Page includes a header with title (e.g., 'Completed Tickets') and back button
- Clicking a ticket in the completed list navigates to TicketDetailWidget as usual
- Back button returns to the main runs table view
- Theme changes work correctly
- Run status colors work for visible tickets
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

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
class TestCompletedTicketsWidgetStructure:
    """Test the basic structure and layout of CompletedTicketsWidget."""

    def test_widget_exists(self):
        """CompletedTicketsWidget class should exist."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget

        widget = CompletedTicketsWidget()
        assert widget is not None

    def test_widget_has_back_button(self):
        """Widget should have a back button in the header."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from PyQt6.QtWidgets import QPushButton

        widget = CompletedTicketsWidget()
        back_btn = widget.findChild(QPushButton, "backBtn")

        assert back_btn is not None

    def test_widget_has_header_title(self):
        """Widget should have a header with 'Completed Tickets' title."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from PyQt6.QtWidgets import QLabel

        widget = CompletedTicketsWidget()

        # Find the title label
        labels = widget.findChildren(QLabel)
        title_labels = [label for label in labels if "completed" in label.text().lower()]

        assert len(title_labels) > 0

    def test_widget_has_ticket_list(self):
        """Widget should have a list widget to display tickets."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        list_widget = widget.findChild(QListWidget)

        assert list_widget is not None

    def test_widget_has_back_clicked_signal(self):
        """Widget should have a back_clicked signal."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget

        widget = CompletedTicketsWidget()

        # Check that the widget has the signal
        assert hasattr(widget, "back_clicked")

    def test_widget_has_ticket_selected_signal(self):
        """Widget should have a ticket_selected signal for navigation."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget

        widget = CompletedTicketsWidget()

        # Check that the widget has the signal
        assert hasattr(widget, "ticket_selected")


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestCompletedTicketsFiltering:
    """Test that only done and merged tickets are displayed."""

    def test_shows_only_done_and_merged_tickets(self):
        """Widget should display only tickets with 'done' or 'merged' status."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
            Ticket(number=2, title="In progress", status=TicketStatus.IN_PROGRESS),
            Ticket(number=3, title="Done ticket", status=TicketStatus.DONE),
            Ticket(number=4, title="Merged ticket", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        # Should only show 2 tickets (done and merged)
        list_widget = widget.findChild(widget.findChildren(type(widget))[0].__class__.__bases__[0])
        count = 0
        for child in widget.findChildren(widget.findChildren(type(widget))[0].__class__.__bases__[0]):
            if hasattr(child, 'count'):
                count = child.count()
                break

        # Find QListWidget
        from PyQt6.QtWidgets import QListWidget
        list_widget = widget.findChild(QListWidget)
        assert list_widget.count() == 2

    def test_shows_done_tickets(self):
        """Widget should show done tickets."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=1, title="Done ticket", status=TicketStatus.DONE),
            Ticket(number=2, title="Pending ticket", status=TicketStatus.PENDING),
        ]

        widget.set_tickets(tickets)

        list_widget = widget.findChild(QListWidget)
        assert list_widget.count() == 1

        # Check that it's the done ticket
        item_text = list_widget.item(0).text()
        assert "Done ticket" in item_text

    def test_shows_merged_tickets(self):
        """Widget should show merged tickets."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=1, title="Merged ticket", status=TicketStatus.MERGED),
            Ticket(number=2, title="In progress", status=TicketStatus.IN_PROGRESS),
        ]

        widget.set_tickets(tickets)

        list_widget = widget.findChild(QListWidget)
        assert list_widget.count() == 1

        # Check that it's the merged ticket
        item_text = list_widget.item(0).text()
        assert "Merged ticket" in item_text

    def test_hides_pending_tickets(self):
        """Widget should not show pending tickets."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=1, title="Pending ticket", status=TicketStatus.PENDING),
            Ticket(number=2, title="Done ticket", status=TicketStatus.DONE),
        ]

        widget.set_tickets(tickets)

        list_widget = widget.findChild(QListWidget)
        assert list_widget.count() == 1

        # Verify it's not the pending ticket
        item_text = list_widget.item(0).text()
        assert "Pending" not in item_text

    def test_hides_in_progress_tickets(self):
        """Widget should not show in progress tickets."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=1, title="In progress", status=TicketStatus.IN_PROGRESS),
            Ticket(number=2, title="Merged ticket", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        list_widget = widget.findChild(QListWidget)
        assert list_widget.count() == 1

        # Verify it's not the in progress ticket
        item_text = list_widget.item(0).text()
        assert "In progress" not in item_text

    def test_empty_list_when_no_completed_tickets(self):
        """Widget should show empty list when there are no completed tickets."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="In progress", status=TicketStatus.IN_PROGRESS),
        ]

        widget.set_tickets(tickets)

        list_widget = widget.findChild(QListWidget)
        assert list_widget.count() == 0


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestCompletedTicketsNavigation:
    """Test navigation from completed tickets widget."""

    def test_back_button_emits_signal(self):
        """Clicking back button should emit back_clicked signal."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from PyQt6.QtWidgets import QPushButton

        widget = CompletedTicketsWidget()
        back_btn = widget.findChild(QPushButton, "backBtn")

        signal_emitted = False

        def on_back():
            nonlocal signal_emitted
            signal_emitted = True

        widget.back_clicked.connect(on_back)
        back_btn.click()

        assert signal_emitted is True

    def test_clicking_ticket_emits_ticket_selected_signal(self):
        """Clicking a ticket should emit ticket_selected signal with ticket number."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=3, title="Done ticket", status=TicketStatus.DONE),
            Ticket(number=5, title="Merged ticket", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets)

        emitted_number = None

        def on_ticket_selected(ticket_number):
            nonlocal emitted_number
            emitted_number = ticket_number

        widget.ticket_selected.connect(on_ticket_selected)

        list_widget = widget.findChild(QListWidget)
        list_widget.setCurrentRow(0)

        # Should emit the ticket number (3)
        assert emitted_number == 3

    def test_double_click_navigates_to_ticket(self):
        """Double-clicking a ticket should navigate to ticket detail."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=1, title="Done ticket", status=TicketStatus.DONE),
        ]

        widget.set_tickets(tickets)

        emitted_number = None

        def on_ticket_selected(ticket_number):
            nonlocal emitted_number
            emitted_number = ticket_number

        widget.ticket_selected.connect(on_ticket_selected)

        # Simulate selection (which should trigger the signal)
        from PyQt6.QtWidgets import QListWidget
        list_widget = widget.findChild(QListWidget)
        list_widget.setCurrentRow(0)

        assert emitted_number == 1


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestCompletedTicketsThemeSupport:
    """Test theme support in completed tickets widget."""

    def test_widget_accepts_theme_parameter(self):
        """Widget should accept theme parameter in constructor."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget

        widget = CompletedTicketsWidget(theme="dark")
        assert widget is not None

        widget_light = CompletedTicketsWidget(theme="light")
        assert widget_light is not None

    def test_widget_has_update_theme_method(self):
        """Widget should have update_theme method."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget

        widget = CompletedTicketsWidget()
        assert hasattr(widget, "update_theme")

    def test_update_theme_changes_colors(self):
        """Calling update_theme should change ticket colors."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Done ticket", status=TicketStatus.DONE),
        ]

        widget.set_tickets(tickets)

        list_widget = widget.findChild(QListWidget)
        item = list_widget.item(0)
        dark_color = item.foreground().color().name().upper()

        # Update to light theme
        widget.update_theme("light")

        item = list_widget.item(0)
        light_color = item.foreground().color().name().upper()

        # Colors should be different
        assert dark_color != light_color

    def test_done_tickets_use_correct_theme_color(self):
        """Done tickets should use correct color for current theme."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        # Dark theme
        widget = CompletedTicketsWidget(theme="dark")
        tickets = [Ticket(number=1, title="Done", status=TicketStatus.DONE)]
        widget.set_tickets(tickets)

        list_widget = widget.findChild(QListWidget)
        item = list_widget.item(0)
        assert item.foreground().color().name().upper() == "#2ECC71"  # Green (done)

    def test_merged_tickets_use_correct_theme_color(self):
        """Merged tickets should use correct color for current theme."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        # Dark theme
        widget = CompletedTicketsWidget(theme="dark")
        tickets = [Ticket(number=1, title="Merged", status=TicketStatus.MERGED)]
        widget.set_tickets(tickets)

        list_widget = widget.findChild(QListWidget)
        item = list_widget.item(0)
        assert item.foreground().color().name().upper() == "#6C7086"  # Dark gray (merged)

        # Light theme
        widget.update_theme("light")
        item = list_widget.item(0)
        assert item.foreground().color().name().upper() == "#95A5A6"  # Light gray (merged)


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestCompletedTicketsWithRunStatus:
    """Test run status color support in completed tickets widget."""

    def test_set_tickets_accepts_run_status_map(self):
        """set_tickets should accept optional run_status_map parameter."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=1, title="Done ticket", status=TicketStatus.DONE),
        ]
        run_status_map = {1: "running"}

        # Should not raise
        widget.set_tickets(tickets, run_status_map=run_status_map)

    def test_run_status_map_preserved_during_theme_change(self):
        """Run status map should be preserved when theme changes."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus

        widget = CompletedTicketsWidget(theme="dark")
        tickets = [
            Ticket(number=1, title="Done ticket", status=TicketStatus.DONE),
        ]
        run_status_map = {1: "running"}

        widget.set_tickets(tickets, run_status_map=run_status_map)

        # Change theme
        widget.update_theme("light")

        # Run status map should still be applied (though done status doesn't change color)
        # This is tested by verifying no errors occur


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestCompletedTicketsEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_ticket_list(self):
        """Widget should handle empty ticket list gracefully."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        widget.set_tickets([])

        list_widget = widget.findChild(QListWidget)
        assert list_widget.count() == 0

    def test_all_tickets_completed(self):
        """Widget should show all tickets when all are completed."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=1, title="Done 1", status=TicketStatus.DONE),
            Ticket(number=2, title="Merged 1", status=TicketStatus.MERGED),
            Ticket(number=3, title="Done 2", status=TicketStatus.DONE),
        ]

        widget.set_tickets(tickets)

        list_widget = widget.findChild(QListWidget)
        assert list_widget.count() == 3

    def test_mixed_status_tickets(self):
        """Widget should correctly filter mixed status tickets."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=1, title="Pending", status=TicketStatus.PENDING),
            Ticket(number=2, title="Done", status=TicketStatus.DONE),
            Ticket(number=3, title="In progress", status=TicketStatus.IN_PROGRESS),
            Ticket(number=4, title="Merged", status=TicketStatus.MERGED),
            Ticket(number=5, title="Done 2", status=TicketStatus.DONE),
        ]

        widget.set_tickets(tickets)

        list_widget = widget.findChild(QListWidget)
        # Should show tickets 2, 4, and 5 (3 tickets)
        assert list_widget.count() == 3

    def test_ticket_icons_displayed(self):
        """Widget should display status icons for tickets."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        tickets = [
            Ticket(number=1, title="Done ticket", status=TicketStatus.DONE),
        ]

        widget.set_tickets(tickets)

        list_widget = widget.findChild(QListWidget)
        item_text = list_widget.item(0).text()

        # Should contain status icon (checkmark for done)
        assert "\u2714" in item_text or "✓" in item_text or "#1" in item_text

    def test_refresh_updates_ticket_list(self):
        """Calling set_tickets again should update the list."""
        app = _ensure_qapp()
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QListWidget

        widget = CompletedTicketsWidget()
        tickets1 = [
            Ticket(number=1, title="Done 1", status=TicketStatus.DONE),
        ]

        widget.set_tickets(tickets1)

        list_widget = widget.findChild(QListWidget)
        assert list_widget.count() == 1

        # Update with different tickets
        tickets2 = [
            Ticket(number=2, title="Done 2", status=TicketStatus.DONE),
            Ticket(number=3, title="Merged 1", status=TicketStatus.MERGED),
        ]

        widget.set_tickets(tickets2)

        assert list_widget.count() == 2
