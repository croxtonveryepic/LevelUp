"""Integration tests for complete ticket image workflow (paste → save → load → delete)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.regression

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QMimeData
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from levelup.core.tickets import add_ticket, delete_ticket, read_tickets


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestEndToEndImageWorkflow:
    """Test complete workflow: create ticket → paste image → save → load → verify."""

    def test_complete_workflow(self, qapp, tmp_path):
        """Complete workflow from creating ticket to loading it back with images."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        # Setup
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)

        # Step 1: Create new ticket
        ticket = add_ticket(tmp_path, "Image bug report", "Initial description")
        widget.set_ticket(ticket)

        # Step 2: Paste image
        mime_data = QMimeData()
        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)

        # Step 3: Add descriptive text
        widget._desc_edit.insertPlainText("\nThis shows the error.")

        # Step 4: Save ticket
        widget.save_ticket()

        # Step 5: Verify file was saved to markdown
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert "ticket-assets" in tickets[0].description or "![" in tickets[0].description

        # Step 6: Verify image file exists
        asset_dir = tmp_path / "levelup" / "ticket-assets"
        assert asset_dir.exists()
        image_files = list(asset_dir.glob("ticket-1-*"))
        assert len(image_files) > 0

        # Step 7: Load ticket in new widget (simulating reload)
        widget2 = TicketDetailWidget(project_path=tmp_path)
        widget2.set_ticket(tickets[0])

        # Step 8: Verify image displays
        html = widget2._desc_edit.toHtml()
        assert "<img" in html

        # Step 9: Verify text is preserved
        text = widget2._desc_edit.toPlainText()
        assert "This shows the error" in text

    def test_multiple_images_workflow(self, qapp, tmp_path):
        """Workflow with multiple images in one ticket."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Multi-image report", "")
        widget.set_ticket(ticket)

        # Add text and images
        widget._desc_edit.setPlainText("Step 1 screenshot:\n")

        mime_data1 = QMimeData()
        img1 = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data1.setImageData(img1)
        widget._desc_edit.insertFromMimeData(mime_data1)

        widget._desc_edit.insertPlainText("\nStep 2 screenshot:\n")

        mime_data2 = QMimeData()
        img2 = QImage(60, 60, QImage.Format.Format_ARGB32)
        mime_data2.setImageData(img2)
        widget._desc_edit.insertFromMimeData(mime_data2)

        widget._desc_edit.insertPlainText("\nConclusion")

        # Save
        widget.save_ticket()

        # Verify 2 images saved
        asset_dir = tmp_path / "levelup" / "ticket-assets"
        images = list(asset_dir.glob("ticket-1-*"))
        assert len(images) == 2

        # Load and verify
        tickets = read_tickets(tmp_path)
        widget2 = TicketDetailWidget(project_path=tmp_path)
        widget2.set_ticket(tickets[0])

        html = widget2._desc_edit.toHtml()
        assert html.count("<img") == 2

    def test_edit_existing_ticket_add_image(self, qapp, tmp_path):
        """Edit existing ticket to add image."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket without image
        ticket = add_ticket(tmp_path, "Bug", "Original text only")

        # Load and add image
        widget = TicketDetailWidget(project_path=tmp_path)
        widget.set_ticket(ticket)

        widget._desc_edit.insertPlainText("\nAdding screenshot:\n")

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)

        widget.save_ticket()

        # Verify
        tickets = read_tickets(tmp_path)
        assert "ticket-assets" in tickets[0].description or "![" in tickets[0].description

    def test_edit_ticket_remove_image(self, qapp, tmp_path):
        """Edit ticket to remove image and verify cleanup."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket with image
        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Bug", "")
        widget.set_ticket(ticket)

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)
        widget.save_ticket()

        asset_dir = tmp_path / "levelup" / "ticket-assets"
        assert len(list(asset_dir.glob("ticket-1-*"))) > 0

        # Remove image by clearing description
        widget._desc_edit.setPlainText("No more images")
        widget.save_ticket()

        # Verify cleanup
        assert len(list(asset_dir.glob("ticket-1-*"))) == 0


class TestTicketDeletionWorkflow:
    """Test ticket deletion with image cleanup."""

    def test_delete_ticket_with_images(self, qapp, tmp_path):
        """Deleting ticket should remove all associated images."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket with multiple images
        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Test", "")
        widget.set_ticket(ticket)

        for i in range(3):
            mime_data = QMimeData()
            image = QImage(50, 50, QImage.Format.Format_ARGB32)
            mime_data.setImageData(image)
            widget._desc_edit.insertFromMimeData(mime_data)

        widget.save_ticket()

        asset_dir = tmp_path / "levelup" / "ticket-assets"
        images_before = list(asset_dir.glob("ticket-1-*"))
        assert len(images_before) == 3

        # Delete ticket
        delete_ticket(tmp_path, 1)

        # All images should be removed
        images_after = list(asset_dir.glob("ticket-1-*"))
        assert len(images_after) == 0

    def test_delete_one_ticket_preserves_others(self, qapp, tmp_path):
        """Deleting one ticket should not affect other tickets."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)

        # Create 3 tickets with images
        for i in range(1, 4):
            ticket = add_ticket(tmp_path, f"Ticket {i}", "")
            widget.set_ticket(ticket)

            mime_data = QMimeData()
            image = QImage(50, 50, QImage.Format.Format_ARGB32)
            mime_data.setImageData(image)
            widget._desc_edit.insertFromMimeData(mime_data)
            widget.save_ticket()

        asset_dir = tmp_path / "levelup" / "ticket-assets"

        # Verify all have images
        assert len(list(asset_dir.glob("ticket-1-*"))) > 0
        assert len(list(asset_dir.glob("ticket-2-*"))) > 0
        assert len(list(asset_dir.glob("ticket-3-*"))) > 0

        # Delete ticket 2
        delete_ticket(tmp_path, 2)

        # Ticket 2 images gone, others remain
        assert len(list(asset_dir.glob("ticket-1-*"))) > 0
        assert len(list(asset_dir.glob("ticket-2-*"))) == 0
        assert len(list(asset_dir.glob("ticket-3-*"))) > 0


class TestImagePersistenceAcrossSessions:
    """Test that images persist across widget instances (simulating app restarts)."""

    def test_images_persist_across_widget_instances(self, qapp, tmp_path):
        """Images should persist when widget is destroyed and recreated."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Session 1: Create and save
        widget1 = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Persistent", "")
        widget1.set_ticket(ticket)

        mime_data = QMimeData()
        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget1._desc_edit.insertFromMimeData(mime_data)
        widget1.save_ticket()

        # Destroy widget
        del widget1

        # Session 2: Load in new widget
        widget2 = TicketDetailWidget(project_path=tmp_path)
        tickets = read_tickets(tmp_path)
        widget2.set_ticket(tickets[0])

        # Image should still display
        html = widget2._desc_edit.toHtml()
        assert "<img" in html

        # Image file should exist
        asset_dir = tmp_path / "levelup" / "ticket-assets"
        images = list(asset_dir.glob("ticket-1-*"))
        assert len(images) > 0


class TestMultiTicketImageIsolation:
    """Test that images from different tickets don't interfere."""

    def test_images_isolated_per_ticket(self, qapp, tmp_path):
        """Each ticket should have isolated image storage."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)

        # Create ticket 1 with image
        t1 = add_ticket(tmp_path, "Ticket 1", "")
        widget.set_ticket(t1)
        mime_data = QMimeData()
        img1 = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(img1)
        widget._desc_edit.insertFromMimeData(mime_data)
        widget.save_ticket()

        # Create ticket 2 with different image
        t2 = add_ticket(tmp_path, "Ticket 2", "")
        widget.set_ticket(t2)
        mime_data2 = QMimeData()
        img2 = QImage(60, 60, QImage.Format.Format_ARGB32)
        mime_data2.setImageData(img2)
        widget._desc_edit.insertFromMimeData(mime_data2)
        widget.save_ticket()

        # Verify separate image files
        asset_dir = tmp_path / "levelup" / "ticket-assets"
        t1_images = list(asset_dir.glob("ticket-1-*"))
        t2_images = list(asset_dir.glob("ticket-2-*"))

        assert len(t1_images) == 1
        assert len(t2_images) == 1
        assert t1_images[0] != t2_images[0]


class TestErrorRecovery:
    """Test error handling and recovery scenarios."""

    def test_corrupted_image_reference_doesnt_crash(self, qapp, tmp_path):
        """Ticket with corrupted image reference should load without crashing."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket with invalid image path
        ticket = add_ticket(tmp_path, "Corrupted", "![Bad](../../../etc/passwd)")

        widget = TicketDetailWidget(project_path=tmp_path)

        # Should not crash
        try:
            widget.set_ticket(ticket)
            assert True
        except Exception:
            pytest.fail("Should handle corrupted references gracefully")

    def test_missing_asset_directory_created_on_save(self, qapp, tmp_path):
        """Missing asset directory should be created on save."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Don't create asset directory
        asset_dir = tickets_dir / "ticket-assets"
        assert not asset_dir.exists()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Test", "")
        widget.set_ticket(ticket)

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)

        # Save should create directory
        widget.save_ticket()

        assert asset_dir.exists()

    def test_readonly_filesystem_handled_gracefully(self, qapp, tmp_path):
        """Read-only filesystem should be handled gracefully."""
        # This test is platform-specific and may be skipped
        pytest.skip("Platform-specific test for read-only filesystems")


class TestBackwardCompatibility:
    """Test that existing tickets without images continue to work."""

    def test_old_tickets_without_images_work(self, qapp, tmp_path):
        """Tickets created before image feature should still work."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create old-style ticket (plain text only)
        ticket = add_ticket(tmp_path, "Old ticket", "Plain text description")

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.set_ticket(ticket)

        # Should load normally
        text = widget._desc_edit.toPlainText()
        assert "Plain text description" in text

        # Should still be able to save
        widget._desc_edit.insertPlainText("\nAdditional text")
        widget.save_ticket()

        # Should load back correctly
        tickets = read_tickets(tmp_path)
        assert "Additional text" in tickets[0].description

    def test_mixed_old_and_new_tickets(self, qapp, tmp_path):
        """File with mix of old (no images) and new (with images) tickets should work."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)

        # Old-style ticket
        t1 = add_ticket(tmp_path, "Old", "Plain text")

        # New-style ticket with image
        t2 = add_ticket(tmp_path, "New", "")
        widget.set_ticket(t2)
        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)
        widget.save_ticket()

        # Both should load correctly
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 2
        assert tickets[0].description == "Plain text"
        assert "ticket-assets" in tickets[1].description or "![" in tickets[1].description


class TestConcurrentModification:
    """Test handling of concurrent modifications (edge case for future multi-user)."""

    def test_save_ticket_after_external_modification(self, qapp, tmp_path):
        """Saving after external DB modification should handle gracefully."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core.tickets import update_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Test", "Original")
        widget.set_ticket(ticket)

        # Simulate external modification via DB
        update_ticket(tmp_path, 1, description="Modified externally")

        # Now save from widget
        widget._desc_edit.insertPlainText("\nWidget change")

        # Should handle gracefully (may overwrite or merge)
        try:
            widget.save_ticket()
        except Exception:
            pytest.fail("Should handle concurrent modification gracefully")
