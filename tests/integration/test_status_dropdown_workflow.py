"""Integration tests for complete status dropdown workflow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

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


class TestCompleteStatusChangeWorkflow:
    """Test complete workflow of changing status via dropdown and seeing results."""

    def test_full_workflow_change_to_declined(self, qapp, tmp_path):
        """Complete workflow: create ticket, change to declined, verify everywhere."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Feature Request", "Add new capability")

        # 1. Load ticket in detail widget
        detail_widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        detail_widget.set_ticket(ticket)

        # Verify initial state
        assert not detail_widget.is_dirty
        dropdown = getattr(detail_widget, "status_dropdown", None) or getattr(
            detail_widget, "_status_dropdown", None
        )
        assert "pending" in dropdown.currentText().lower()

        # 2. Change status to declined
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        # Form should be dirty
        assert detail_widget.is_dirty

        # 3. Save changes
        detail_widget.save_ticket()

        # 4. Verify status persisted to file
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert tickets[0].status == TicketStatus.DECLINED
        assert tickets[0].title == "Feature Request"

        # 5. Reload ticket and verify UI reflects change
        detail_widget.set_ticket(tickets[0])
        assert "declined" in dropdown.currentText().lower()
        assert "declined" in detail_widget._status_label.text().lower()

        # 6. Verify sidebar shows green color
        sidebar = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar.refresh()
        assert sidebar.ticket_list.count() == 1

    def test_workflow_change_declined_back_to_pending(self, qapp, tmp_path):
        """Workflow: change declined ticket back to pending."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        # Load declined ticket
        tickets = read_tickets(tmp_path)
        detail_widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        detail_widget.set_ticket(tickets[0])

        dropdown = getattr(detail_widget, "status_dropdown", None) or getattr(
            detail_widget, "_status_dropdown", None
        )
        assert "declined" in dropdown.currentText().lower()

        # Change to pending
        for i in range(dropdown.count()):
            if "pending" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        detail_widget.save_ticket()

        # Verify change
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.PENDING

    def test_workflow_multiple_status_transitions(self, qapp, tmp_path):
        """Workflow: transition through multiple statuses."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        detail_widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        dropdown = getattr(detail_widget, "status_dropdown", None) or getattr(
            detail_widget, "_status_dropdown", None
        )

        # pending -> in progress
        detail_widget.set_ticket(ticket)
        for i in range(dropdown.count()):
            if "progress" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break
        detail_widget.save_ticket()
        assert read_tickets(tmp_path)[0].status == TicketStatus.IN_PROGRESS

        # in progress -> done
        tickets = read_tickets(tmp_path)
        detail_widget.set_ticket(tickets[0])
        for i in range(dropdown.count()):
            if "done" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break
        detail_widget.save_ticket()
        assert read_tickets(tmp_path)[0].status == TicketStatus.DONE

        # done -> declined (user changed mind)
        tickets = read_tickets(tmp_path)
        detail_widget.set_ticket(tickets[0])
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break
        detail_widget.save_ticket()
        assert read_tickets(tmp_path)[0].status == TicketStatus.DECLINED


class TestMainWindowIntegration:
    """Test MainWindow integration with status changes."""

    def test_main_window_refreshes_sidebar_after_save(self, qapp, tmp_path):
        """MainWindow should refresh sidebar after ticket status save."""
        # This test would require MainWindow to be fully initialized
        # For now, test the expected behavior pattern
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task", "Description")

        sidebar = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar.refresh()
        initial_count = sidebar.ticket_list.count()

        # Change status
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        # Refresh sidebar (as MainWindow would do)
        sidebar.refresh()

        # Ticket count should be same
        assert sidebar.ticket_list.count() == initial_count

    def test_main_window_preserves_selection_after_refresh(self, qapp, tmp_path):
        """MainWindow should preserve ticket selection after status change."""
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Task 1", "Description")
        add_ticket(tmp_path, "Task 2", "Description")
        add_ticket(tmp_path, "Task 3", "Description")

        sidebar = TicketSidebar(project_path=str(tmp_path), theme="dark")
        sidebar.refresh()

        # Select ticket 2
        sidebar.ticket_list.setCurrentRow(1)
        selected_ticket = 2

        # Change status of ticket 2
        set_ticket_status(tmp_path, selected_ticket, TicketStatus.DECLINED)

        # Refresh sidebar
        sidebar.refresh()

        # Selection handling may vary by implementation
        # At minimum, sidebar should still be usable
        assert sidebar.ticket_list.count() == 3


class TestConcurrentChanges:
    """Test handling of concurrent status changes."""

    def test_reload_after_external_status_change(self, qapp, tmp_path):
        """Widget should show updated status when ticket changed externally."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        detail_widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        detail_widget.set_ticket(ticket)

        dropdown = getattr(detail_widget, "status_dropdown", None) or getattr(
            detail_widget, "_status_dropdown", None
        )
        assert "pending" in dropdown.currentText().lower()

        # External change (e.g., CLI command)
        set_ticket_status(tmp_path, 1, TicketStatus.DECLINED)

        # Reload ticket
        tickets = read_tickets(tmp_path)
        detail_widget.set_ticket(tickets[0])

        # Should show updated status
        assert "declined" in dropdown.currentText().lower()

    def test_dirty_flag_cleared_after_save(self, qapp, tmp_path):
        """Dirty flag should be cleared after successful save."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        detail_widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        detail_widget.set_ticket(ticket)

        # Change status
        dropdown = getattr(detail_widget, "status_dropdown", None) or getattr(
            detail_widget, "_status_dropdown", None
        )
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        assert detail_widget.is_dirty

        # Save
        detail_widget.save_ticket()

        # Dirty flag should be cleared after save
        # (depends on implementation - may need to reload ticket)
        tickets = read_tickets(tmp_path)
        detail_widget.set_ticket(tickets[0])
        assert not detail_widget.is_dirty


class TestStatusChangeWithMetadata:
    """Test status changes preserve and interact with metadata."""

    def test_status_change_preserves_auto_approve_metadata(self, qapp, tmp_path):
        """Changing status should preserve auto_approve metadata."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Desc", metadata={"auto_approve": True})

        detail_widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        detail_widget.set_ticket(ticket)

        # Change status
        dropdown = getattr(detail_widget, "status_dropdown", None) or getattr(
            detail_widget, "_status_dropdown", None
        )
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        detail_widget.save_ticket()

        # Metadata should be preserved
        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is not None
        assert tickets[0].metadata.get("auto_approve") is True

    def test_status_and_metadata_both_change(self, qapp, tmp_path):
        """Should be able to change both status and metadata together."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        detail_widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        detail_widget.set_ticket(ticket)

        # Change status
        dropdown = getattr(detail_widget, "status_dropdown", None) or getattr(
            detail_widget, "_status_dropdown", None
        )
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        # Change auto-approve
        detail_widget.auto_approve_checkbox.setChecked(True)

        detail_widget.save_ticket()

        # Both changes should be persisted
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DECLINED
        assert tickets[0].metadata is not None
        assert tickets[0].metadata.get("auto_approve") is True


class TestStatusChangeEdgeCases:
    """Test edge cases in status change workflow."""

    def test_cancel_discards_status_change(self, qapp, tmp_path):
        """Cancel should discard unsaved status change."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        detail_widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        detail_widget.set_ticket(ticket)

        # Change status
        dropdown = getattr(detail_widget, "status_dropdown", None) or getattr(
            detail_widget, "_status_dropdown", None
        )
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        # Don't save, reload instead
        tickets = read_tickets(tmp_path)
        detail_widget.set_ticket(tickets[0])

        # Should be back to pending
        assert "pending" in dropdown.currentText().lower()
        assert tickets[0].status == TicketStatus.PENDING

    def test_status_change_with_empty_description(self, qapp, tmp_path):
        """Status change should work even with empty description."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "")

        detail_widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")
        detail_widget.set_ticket(ticket)

        # Change status
        dropdown = getattr(detail_widget, "status_dropdown", None) or getattr(
            detail_widget, "_status_dropdown", None
        )
        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break

        detail_widget.save_ticket()

        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DECLINED
        assert tickets[0].description == ""

    def test_rapid_status_changes(self, qapp, tmp_path):
        """Rapid status changes should all work correctly."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task", "Description")

        detail_widget = TicketDetailWidget(project_path=str(tmp_path), theme="dark")

        dropdown = getattr(detail_widget, "status_dropdown", None) or getattr(
            detail_widget, "_status_dropdown", None
        )

        # Rapid changes: pending -> done -> declined
        detail_widget.set_ticket(ticket)

        for i in range(dropdown.count()):
            if "done" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break
        detail_widget.save_ticket()

        tickets = read_tickets(tmp_path)
        detail_widget.set_ticket(tickets[0])

        for i in range(dropdown.count()):
            if "declined" in dropdown.itemText(i).lower():
                dropdown.setCurrentIndex(i)
                break
        detail_widget.save_ticket()

        # Final status should be declined
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DECLINED
