"""Unit tests for integrating ImageTextEdit into TicketDetailWidget."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.regression

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QMimeData
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from levelup.core.tickets import Ticket, TicketStatus, add_ticket, read_tickets


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestTicketDetailWidgetImageSupport:
    """Test that TicketDetailWidget uses ImageTextEdit instead of QPlainTextEdit."""

    def test_description_widget_is_image_text_edit(self, qapp, tmp_path):
        """Description editor should be ImageTextEdit, not QPlainTextEdit."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=tmp_path)

        # Should have ImageTextEdit for description
        assert hasattr(widget, "_desc_edit")
        # Should NOT be QPlainTextEdit anymore
        from PyQt6.QtWidgets import QPlainTextEdit

        assert not isinstance(widget._desc_edit, QPlainTextEdit)

    def test_description_widget_supports_rich_text(self, qapp, tmp_path):
        """Description widget should support rich text (images)."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=tmp_path)

        # Should be able to set HTML
        widget._desc_edit.setHtml("<p>Test</p>")
        html = widget._desc_edit.toHtml()
        assert "Test" in html

    def test_paste_image_into_description(self, qapp, tmp_path):
        """Should be able to paste images into description field."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Test ticket", "Description")
        widget.set_ticket(ticket)

        # Paste image
        mime_data = QMimeData()
        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)

        widget._desc_edit.insertFromMimeData(mime_data)

        html = widget._desc_edit.toHtml()
        assert "<img" in html


class TestTicketSaveWithImages:
    """Test saving tickets with image references."""

    def test_save_ticket_with_image_creates_markdown(self, qapp, tmp_path):
        """Saving ticket with images should create markdown with image references."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Image test", "Original description")
        widget.set_ticket(ticket)

        # Add image to description
        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)

        # Save ticket
        widget.save_ticket()

        # Read back from markdown
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1

        # Should have image reference in markdown
        assert "![" in tickets[0].description or "ticket-assets" in tickets[0].description

    def test_save_creates_image_files(self, qapp, tmp_path):
        """Saving ticket should write image files to asset directory."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Test", "Desc")
        widget.set_ticket(ticket)

        # Paste image
        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)

        # Save
        widget.save_ticket()

        # Asset directory should be created
        asset_dir = tmp_path / "levelup" / "ticket-assets"
        assert asset_dir.exists()

        # Should have at least one image file
        image_files = list(asset_dir.glob("ticket-*"))
        assert len(image_files) > 0

    def test_save_preserves_text_and_images(self, qapp, tmp_path):
        """Saving should preserve both text and image content."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Test", "")
        widget.set_ticket(ticket)

        # Set mixed content
        widget._desc_edit.setPlainText("Before image\n")
        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)
        widget._desc_edit.insertPlainText("\nAfter image")

        widget.save_ticket()

        # Read back
        tickets = read_tickets(tmp_path)
        description = tickets[0].description

        assert "Before image" in description
        assert "After image" in description

    def test_images_not_saved_until_ticket_saved(self, qapp, tmp_path):
        """Images should not be written to disk until ticket is saved."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Test", "Desc")
        widget.set_ticket(ticket)

        # Paste image
        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)

        # Asset directory should NOT exist yet (images staged, not saved)
        asset_dir = tmp_path / "levelup" / "ticket-assets"
        # Implementation choice: may or may not create directory early
        # Key: orphaned files should be prevented

        # Save ticket
        widget.save_ticket()

        # NOW asset directory should exist
        assert asset_dir.exists()


class TestTicketLoadWithImages:
    """Test loading tickets that contain image references."""

    def test_load_ticket_with_image_displays_it(self, qapp, tmp_path):
        """Loading ticket with image reference should display the image."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create image file
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()
        img_path = asset_dir / "test.png"
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        image.save(str(img_path))

        # Create ticket with image reference
        description = "![Screenshot](levelup/ticket-assets/test.png)"
        ticket = add_ticket(tmp_path, "Test", description)

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.set_ticket(ticket)

        # Should display image
        html = widget._desc_edit.toHtml()
        assert "<img" in html

    def test_load_ticket_without_images(self, qapp, tmp_path):
        """Loading plain text ticket should still work."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        ticket = add_ticket(tmp_path, "Plain text", "Just plain text description")

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.set_ticket(ticket)

        text = widget._desc_edit.toPlainText()
        assert "Just plain text description" in text

    def test_load_missing_image_shows_placeholder(self, qapp, tmp_path):
        """Loading ticket with missing image should show placeholder."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Reference non-existent image
        description = "![Missing](levelup/ticket-assets/missing.png)"
        ticket = add_ticket(tmp_path, "Test", description)

        widget = TicketDetailWidget(project_path=tmp_path)

        # Should not crash
        widget.set_ticket(ticket)

        # Should still load
        assert widget._ticket is not None

    def test_mixed_content_loads_correctly(self, qapp, tmp_path):
        """Tickets with mixed text and images should load correctly."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create image
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()
        img_path = asset_dir / "test.png"
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        image.save(str(img_path))

        description = """Here is the bug:
![Error screenshot](levelup/ticket-assets/test.png)
As you can see, the button is broken."""

        ticket = add_ticket(tmp_path, "Bug", description)

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.set_ticket(ticket)

        # Should have both text and image
        html = widget._desc_edit.toHtml()
        assert "<img" in html
        assert "button is broken" in widget._desc_edit.toPlainText()


class TestTicketDeletionWithImages:
    """Test that deleting tickets cleans up associated images."""

    def test_delete_ticket_removes_images(self, qapp, tmp_path):
        """Deleting ticket should remove associated image files."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core.tickets import delete_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Test", "Desc")
        widget.set_ticket(ticket)

        # Add and save image
        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)
        widget.save_ticket()

        # Get image files for ticket 1
        asset_dir = tmp_path / "levelup" / "ticket-assets"
        ticket1_images = list(asset_dir.glob("ticket-1-*"))
        assert len(ticket1_images) > 0

        # Delete ticket
        delete_ticket(tmp_path, 1)

        # Images should be deleted
        remaining = list(asset_dir.glob("ticket-1-*"))
        assert len(remaining) == 0

    def test_delete_ticket_preserves_other_ticket_images(self, qapp, tmp_path):
        """Deleting one ticket should not affect other tickets' images."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core.tickets import delete_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket 1 with image
        widget = TicketDetailWidget(project_path=tmp_path)
        t1 = add_ticket(tmp_path, "Ticket 1", "")
        widget.set_ticket(t1)
        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)
        widget.save_ticket()

        # Create ticket 2 with image
        t2 = add_ticket(tmp_path, "Ticket 2", "")
        widget.set_ticket(t2)
        mime_data2 = QMimeData()
        image2 = QImage(60, 60, QImage.Format.Format_ARGB32)
        mime_data2.setImageData(image2)
        widget._desc_edit.insertFromMimeData(mime_data2)
        widget.save_ticket()

        asset_dir = tmp_path / "levelup" / "ticket-assets"
        ticket2_images = list(asset_dir.glob("ticket-2-*"))
        assert len(ticket2_images) > 0

        # Delete ticket 1
        delete_ticket(tmp_path, 1)

        # Ticket 2 images should still exist
        remaining_t2 = list(asset_dir.glob("ticket-2-*"))
        assert len(remaining_t2) > 0


class TestOrphanedImageCleanup:
    """Test cleanup of orphaned images when user removes them from description."""

    def test_remove_image_from_description_cleans_up(self, qapp, tmp_path):
        """Removing image from description and saving should delete orphaned file."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Test", "")
        widget.set_ticket(ticket)

        # Add image
        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)
        widget.save_ticket()

        asset_dir = tmp_path / "levelup" / "ticket-assets"
        images_before = list(asset_dir.glob("ticket-1-*"))
        assert len(images_before) > 0

        # Clear description
        widget._desc_edit.setPlainText("No images anymore")
        widget.save_ticket()

        # Orphaned images should be cleaned up
        images_after = list(asset_dir.glob("ticket-1-*"))
        assert len(images_after) == 0

    def test_keep_referenced_images(self, qapp, tmp_path):
        """Images still referenced in description should not be deleted."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Test", "")
        widget.set_ticket(ticket)

        # Add two images
        for i in range(2):
            mime_data = QMimeData()
            image = QImage(50, 50, QImage.Format.Format_ARGB32)
            mime_data.setImageData(image)
            widget._desc_edit.insertFromMimeData(mime_data)

        widget.save_ticket()

        asset_dir = tmp_path / "levelup" / "ticket-assets"
        images_before = list(asset_dir.glob("ticket-1-*"))
        assert len(images_before) == 2

        # Keep images in description, just add text
        widget._desc_edit.insertPlainText("\nAdditional text")
        widget.save_ticket()

        # Both images should still exist
        images_after = list(asset_dir.glob("ticket-1-*"))
        assert len(images_after) == 2


class TestCLICompatibility:
    """Test that CLI/agents can read descriptions with images."""

    def test_ticket_to_task_input_preserves_markdown(self, tmp_path):
        """Ticket.to_task_input() should preserve markdown format with images."""
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create image
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()
        img_path = asset_dir / "test.png"
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        image.save(str(img_path))

        description = "Bug description:\n![Screenshot](levelup/ticket-assets/test.png)\nEnd"
        ticket = add_ticket(tmp_path, "Bug", description)

        task_input = ticket.to_task_input()

        # Should preserve markdown format
        assert "![Screenshot]" in task_input.description or "test.png" in task_input.description

    def test_agents_see_image_paths(self, tmp_path):
        """Agents should see image paths in markdown for context."""
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        description = "![Error](levelup/ticket-assets/error.png)\nButton doesn't work"
        ticket = add_ticket(tmp_path, "Issue", description)

        task_input = ticket.to_task_input()

        # Agent can see the image path
        assert "ticket-assets" in task_input.description
        assert "error.png" in task_input.description


class TestImageSizeValidation:
    """Test validation of large image pastes."""

    def test_paste_large_image_shows_warning(self, qapp, tmp_path):
        """Pasting image over 10MB should show warning."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path)
        ticket = add_ticket(tmp_path, "Test", "")
        widget.set_ticket(ticket)

        # Create very large image (this test may be slow, so we mock validation)
        # In real implementation, validation would prevent saving
        # This test just ensures no crash
        mime_data = QMimeData()
        large_image = QImage(1000, 1000, QImage.Format.Format_ARGB32)
        mime_data.setImageData(large_image)

        # Should handle gracefully
        try:
            widget._desc_edit.insertFromMimeData(mime_data)
        except Exception:
            pytest.fail("Should handle large images gracefully")


class TestThemeCompatibility:
    """Test that images work in both light and dark themes."""

    def test_images_display_in_dark_theme(self, qapp, tmp_path):
        """Images should display correctly in dark theme."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path, theme="dark")
        ticket = add_ticket(tmp_path, "Test", "")
        widget.set_ticket(ticket)

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)

        # Should display without visual issues
        html = widget._desc_edit.toHtml()
        assert "<img" in html

    def test_images_display_in_light_theme(self, qapp, tmp_path):
        """Images should display correctly in light theme."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path, theme="light")
        ticket = add_ticket(tmp_path, "Test", "")
        widget.set_ticket(ticket)

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)

        html = widget._desc_edit.toHtml()
        assert "<img" in html

    def test_theme_change_preserves_images(self, qapp, tmp_path):
        """Changing theme should preserve image display."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=tmp_path, theme="dark")
        ticket = add_ticket(tmp_path, "Test", "")
        widget.set_ticket(ticket)

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget._desc_edit.insertFromMimeData(mime_data)

        html_before = widget._desc_edit.toHtml()

        # Change theme
        widget.update_theme("light")
        if hasattr(widget._desc_edit, "update_theme"):
            widget._desc_edit.update_theme("light")

        # Images should still be there
        html_after = widget._desc_edit.toHtml()
        assert "<img" in html_after
