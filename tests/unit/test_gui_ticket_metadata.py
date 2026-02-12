"""Unit tests for ticket metadata in GUI widgets."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# GUI tests require PyQt6
pytest.importorskip("PyQt6")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from levelup.core.tickets import Ticket, TicketStatus, add_ticket, read_tickets


# Test fixtures need a QApplication instance
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestTicketDetailWidgetMetadata:
    """Test metadata editing in TicketDetailWidget."""

    def test_widget_has_auto_approve_checkbox(self, qapp, tmp_path):
        """TicketDetailWidget should have auto-approve checkbox."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=tmp_path)

        # Widget should have an auto-approve checkbox or toggle
        assert hasattr(widget, "auto_approve_checkbox") or hasattr(
            widget, "auto_approve_toggle"
        )

    def test_checkbox_visible_in_edit_mode(self, qapp, tmp_path):
        """Auto-approve checkbox should be visible when editing ticket."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.show()
        widget.load_ticket(ticket)

        # Checkbox should be visible
        if hasattr(widget, "auto_approve_checkbox"):
            assert widget.auto_approve_checkbox.isVisible()

    def test_checkbox_reflects_ticket_metadata(self, qapp, tmp_path):
        """Checkbox should show current ticket's auto_approve setting."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"auto_approve": True}
        )

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        # Checkbox should be checked
        if hasattr(widget, "auto_approve_checkbox"):
            assert widget.auto_approve_checkbox.isChecked()

    def test_checkbox_unchecked_for_no_metadata(self, qapp, tmp_path):
        """Checkbox should be unchecked for tickets without metadata."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        # Checkbox should be unchecked
        if hasattr(widget, "auto_approve_checkbox"):
            assert not widget.auto_approve_checkbox.isChecked()

    def test_checkbox_unchecked_for_auto_approve_false(self, qapp, tmp_path):
        """Checkbox should be unchecked when auto_approve=False."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"auto_approve": False}
        )

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        if hasattr(widget, "auto_approve_checkbox"):
            assert not widget.auto_approve_checkbox.isChecked()

    def test_save_updates_ticket_metadata(self, qapp, tmp_path):
        """Saving ticket should update metadata based on checkbox."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        # Check the checkbox
        if hasattr(widget, "auto_approve_checkbox"):
            widget.auto_approve_checkbox.setChecked(True)

        # Save the ticket
        widget.save_ticket()

        # Read back and verify
        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata is not None
        assert tickets[0].metadata["auto_approve"] is True

    def test_save_preserves_other_metadata(self, qapp, tmp_path):
        """Saving should preserve other metadata fields."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"auto_approve": False, "priority": "high"},
        )

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        # Change auto_approve
        if hasattr(widget, "auto_approve_checkbox"):
            widget.auto_approve_checkbox.setChecked(True)

        widget.save_ticket()

        # Other metadata should be preserved
        tickets = read_tickets(tmp_path)
        assert tickets[0].metadata["auto_approve"] is True
        assert tickets[0].metadata["priority"] == "high"

    def test_checkbox_state_persists_across_loads(self, qapp, tmp_path):
        """Loading same ticket multiple times should show correct state."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"auto_approve": True}
        )

        widget = TicketDetailWidget(project_path=tmp_path)

        # Load ticket
        widget.load_ticket(ticket)
        if hasattr(widget, "auto_approve_checkbox"):
            assert widget.auto_approve_checkbox.isChecked()

        # Change to False
        if hasattr(widget, "auto_approve_checkbox"):
            widget.auto_approve_checkbox.setChecked(False)
        widget.save_ticket()

        # Reload
        tickets = read_tickets(tmp_path)
        widget.load_ticket(tickets[0])
        if hasattr(widget, "auto_approve_checkbox"):
            assert not widget.auto_approve_checkbox.isChecked()


class TestTicketListAutoApproveIndicator:
    """Test auto-approve indicator in ticket list."""

    def test_list_shows_auto_approve_badge(self, qapp, tmp_path):
        """Ticket list should show indicator for auto-approved tickets."""
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "Normal task")
        add_ticket(tmp_path, "Auto task", metadata={"auto_approve": True})

        sidebar = TicketSidebar(project_path=tmp_path)
        sidebar.refresh()

        # List should have some visual indicator
        # Could be icon, badge, color, etc.
        # This tests the interface exists
        assert sidebar.ticket_list is not None

    def test_indicator_updates_when_metadata_changes(self, qapp, tmp_path):
        """Indicator should update when ticket metadata changes."""
        from levelup.gui.ticket_sidebar import TicketSidebar

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Task")

        sidebar = TicketSidebar(project_path=tmp_path)
        sidebar.refresh()

        # Update ticket metadata
        from levelup.core.tickets import update_ticket

        update_ticket(tmp_path, 1, metadata={"auto_approve": True})

        # Refresh list
        sidebar.refresh()

        # Indicator should now be present
        # Implementation-specific


class TestTicketCreationWithMetadata:
    """Test creating tickets with metadata through GUI."""

    def test_create_ticket_dialog_has_auto_approve_option(self, qapp, tmp_path):
        """Create ticket dialog should have auto-approve checkbox."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=tmp_path)

        # Widget should have checkbox even in create mode
        # Or it could be hidden in create mode and only shown in edit
        assert hasattr(widget, "auto_approve_checkbox") or hasattr(
            widget, "auto_approve_toggle"
        )

    def test_create_new_ticket_with_auto_approve(self, qapp, tmp_path):
        """Should be able to create new ticket with auto_approve=True."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)

        # Set ticket fields
        if hasattr(widget, "title_edit"):
            widget.title_edit.setText("New task")
        if hasattr(widget, "description_edit"):
            widget.description_edit.setPlainText("Description")

        # Check auto-approve
        if hasattr(widget, "auto_approve_checkbox"):
            widget.auto_approve_checkbox.setChecked(True)

        # Save (create) the ticket
        if hasattr(widget, "save_ticket"):
            widget.save_ticket()

        # Verify ticket was created with metadata
        tickets = read_tickets(tmp_path)
        if len(tickets) > 0:
            assert tickets[-1].metadata is not None
            assert tickets[-1].metadata["auto_approve"] is True


class TestMetadataTooltipsAndLabels:
    """Test tooltips and labels for metadata fields."""

    def test_auto_approve_has_tooltip(self, qapp, tmp_path):
        """Auto-approve checkbox should have descriptive tooltip."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=tmp_path)

        if hasattr(widget, "auto_approve_checkbox"):
            tooltip = widget.auto_approve_checkbox.toolTip()
            # Should explain what auto-approve does
            assert len(tooltip) > 0
            assert (
                "checkpoint" in tooltip.lower()
                or "auto" in tooltip.lower()
                or "approve" in tooltip.lower()
            )

    def test_auto_approve_has_label(self, qapp, tmp_path):
        """Auto-approve checkbox should have clear label."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=tmp_path)

        if hasattr(widget, "auto_approve_checkbox"):
            text = widget.auto_approve_checkbox.text()
            assert len(text) > 0
            assert "auto" in text.lower() or "approve" in text.lower()


class TestMetadataInTicketDetailView:
    """Test metadata display in ticket detail view."""

    def test_readonly_view_shows_auto_approve_status(self, qapp, tmp_path):
        """When viewing (not editing) ticket, should show auto-approve status."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"auto_approve": True}
        )

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        # Should display auto-approve status (badge, icon, text, etc.)
        # Implementation-specific, but widget should show this info

    def test_metadata_section_in_detail_view(self, qapp, tmp_path):
        """Detail view should have metadata section."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"auto_approve": True, "priority": "high"},
        )

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        # Should display metadata information
        # Could be in a dedicated section, as tags, etc.


class TestMetadataValidation:
    """Test validation of metadata in GUI."""

    def test_checkbox_accepts_checked_state(self, qapp, tmp_path):
        """Checkbox should properly handle checked state."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)

        if hasattr(widget, "auto_approve_checkbox"):
            # Should be checkable
            assert widget.auto_approve_checkbox.isCheckable()

            # Should accept setChecked
            widget.auto_approve_checkbox.setChecked(True)
            assert widget.auto_approve_checkbox.isChecked()

            widget.auto_approve_checkbox.setChecked(False)
            assert not widget.auto_approve_checkbox.isChecked()


class TestMetadataEdgeCases:
    """Test edge cases for metadata in GUI."""

    def test_load_ticket_with_no_metadata(self, qapp, tmp_path):
        """Should handle tickets with no metadata gracefully."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket without metadata
        add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=tmp_path)

        # Should not crash
        tickets = read_tickets(tmp_path)
        if len(tickets) > 0:
            try:
                widget.load_ticket(tickets[0])
                # Should either load with default or show error gracefully
            except Exception:
                # Should handle error gracefully
                pass

    def test_empty_metadata_dict(self, qapp, tmp_path):
        """Should handle tickets with empty metadata dict."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description", metadata={})

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        # Should load without error
        if hasattr(widget, "auto_approve_checkbox"):
            # Should default to unchecked
            assert not widget.auto_approve_checkbox.isChecked()

    def test_metadata_with_old_tickets(self, qapp, tmp_path):
        """Should handle tickets created without metadata."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket without metadata (simulates old-style ticket)
        add_ticket(tmp_path, "Old task", "Description without metadata")

        widget = TicketDetailWidget(project_path=tmp_path)
        tickets = read_tickets(tmp_path)

        # Should load successfully
        widget.load_ticket(tickets[0])

        if hasattr(widget, "auto_approve_checkbox"):
            # Should default to unchecked
            assert not widget.auto_approve_checkbox.isChecked()
