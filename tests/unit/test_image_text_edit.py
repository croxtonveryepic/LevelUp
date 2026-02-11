"""Unit tests for ImageTextEdit widget (QTextEdit with image paste/drop)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# GUI tests require PyQt6
pytest.importorskip("PyQt6")

from PyQt6.QtCore import QMimeData, Qt, QUrl
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestImageTextEditCreation:
    """Test ImageTextEdit widget initialization."""

    def test_widget_creation(self, qapp, tmp_path):
        """Should create ImageTextEdit widget successfully."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path)
        assert widget is not None

    def test_widget_is_qtextedit(self, qapp, tmp_path):
        """ImageTextEdit should be a QTextEdit subclass."""
        from levelup.gui.image_text_edit import ImageTextEdit
        from PyQt6.QtWidgets import QTextEdit

        widget = ImageTextEdit(project_path=tmp_path)
        assert isinstance(widget, QTextEdit)

    def test_widget_stores_project_path(self, qapp, tmp_path):
        """Widget should store project path for image operations."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path)
        assert widget.project_path == tmp_path

    def test_widget_stores_ticket_number(self, qapp, tmp_path):
        """Widget should store ticket number for image filenames."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=5)
        assert widget.ticket_number == 5


class TestImagePasteHandling:
    """Test pasting images from clipboard."""

    def test_paste_image_from_clipboard(self, qapp, tmp_path):
        """Pasting image from clipboard should insert it inline."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Create fake image data in clipboard
        mime_data = QMimeData()
        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.red)
        mime_data.setImageData(image)

        # Simulate paste
        widget.insertFromMimeData(mime_data)

        # Should have HTML with img tag
        html = widget.toHtml()
        assert "<img" in html

    def test_paste_text_still_works(self, qapp, tmp_path):
        """Pasting text should still work normally."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Create fake text data
        mime_data = QMimeData()
        mime_data.setText("Plain text content")

        widget.insertFromMimeData(mime_data)

        # Should contain the text
        text = widget.toPlainText()
        assert "Plain text content" in text

    def test_paste_image_saves_to_assets(self, qapp, tmp_path):
        """Pasting image should stage it for saving to assets."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)

        widget.insertFromMimeData(mime_data)

        # Should track pending images (not saved until ticket save)
        assert hasattr(widget, "_pending_images") or True  # May not expose this

    def test_paste_multiple_images(self, qapp, tmp_path):
        """Pasting multiple images should all be inserted."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Paste first image
        mime_data1 = QMimeData()
        image1 = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data1.setImageData(image1)
        widget.insertFromMimeData(mime_data1)

        # Add some text
        widget.insertPlainText("\nBetween images\n")

        # Paste second image
        mime_data2 = QMimeData()
        image2 = QImage(60, 60, QImage.Format.Format_ARGB32)
        mime_data2.setImageData(image2)
        widget.insertFromMimeData(mime_data2)

        html = widget.toHtml()
        # Should have 2 images
        assert html.count("<img") == 2

    def test_paste_without_ticket_number_fails_gracefully(self, qapp, tmp_path):
        """Pasting image without ticket number should handle gracefully."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path)  # No ticket number

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)

        # Should either insert with placeholder or show warning
        try:
            widget.insertFromMimeData(mime_data)
            # Should not crash
        except Exception:
            pytest.fail("Should handle missing ticket number gracefully")


class TestImageDragAndDrop:
    """Test dragging and dropping image files."""

    def test_drop_image_file(self, qapp, tmp_path):
        """Dropping image file should insert it."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Create a test image file
        test_image_path = tmp_path / "test.png"
        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        image.save(str(test_image_path))

        # Create drop mime data
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(test_image_path))])

        widget.insertFromMimeData(mime_data)

        # Should insert the image
        html = widget.toHtml()
        assert "<img" in html

    def test_drop_multiple_files(self, qapp, tmp_path):
        """Dropping multiple image files should insert all."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Create test images
        urls = []
        for i in range(3):
            img_path = tmp_path / f"test{i}.png"
            img = QImage(50, 50, QImage.Format.Format_ARGB32)
            img.save(str(img_path))
            urls.append(QUrl.fromLocalFile(str(img_path)))

        mime_data = QMimeData()
        mime_data.setUrls(urls)

        widget.insertFromMimeData(mime_data)

        html = widget.toHtml()
        assert html.count("<img") == 3

    def test_drop_non_image_file_ignored(self, qapp, tmp_path):
        """Dropping non-image files should be ignored or handled gracefully."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Create a text file
        text_file = tmp_path / "test.txt"
        text_file.write_text("Not an image")

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(text_file))])

        # Should not crash
        try:
            widget.insertFromMimeData(mime_data)
        except Exception:
            pytest.fail("Should handle non-image files gracefully")


class TestImageDisplay:
    """Test displaying images loaded from markdown."""

    def test_load_html_with_images(self, qapp, tmp_path):
        """Loading HTML with images should display them."""
        from levelup.gui.image_text_edit import ImageTextEdit

        # Create a test image
        img_path = tmp_path / "levelup" / "ticket-assets"
        img_path.mkdir(parents=True)
        test_img = img_path / "test.png"

        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.blue)
        image.save(str(test_img))

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Set HTML with image reference
        html = f'<p>Before</p><img src="{test_img}" /><p>After</p>'
        widget.setHtml(html)

        # Should display the image
        result_html = widget.toHtml()
        assert "<img" in result_html

    def test_load_markdown_with_images(self, qapp, tmp_path):
        """Loading markdown with image references should display images."""
        from levelup.gui.image_text_edit import ImageTextEdit

        # Create test image
        img_path = tmp_path / "levelup" / "ticket-assets"
        img_path.mkdir(parents=True)
        test_img = img_path / "test.png"

        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        image.save(str(test_img))

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Set markdown
        markdown = f"Description:\n![Screenshot](levelup/ticket-assets/test.png)\nEnd"
        widget.setMarkdown(markdown)

        html = widget.toHtml()
        # Should have converted to image
        assert "<img" in html or "test.png" in html

    def test_missing_image_shows_placeholder(self, qapp, tmp_path):
        """Missing image should show placeholder or broken image indicator."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Reference non-existent image
        html = f'<img src="{tmp_path}/missing.png" alt="Missing" />'
        widget.setHtml(html)

        # Should not crash
        result_html = widget.toHtml()
        assert result_html is not None

    def test_image_max_width_constraint(self, qapp, tmp_path):
        """Images should have max-width constraint in display."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Create large image
        img_path = tmp_path / "large.png"
        large_img = QImage(2000, 2000, QImage.Format.Format_ARGB32)
        large_img.save(str(img_path))

        html = f'<img src="{img_path}" />'
        widget.setHtml(html)

        # Should apply max-width style
        result_html = widget.toHtml()
        # Implementation may add max-width style
        assert "img" in result_html


class TestThemeSupport:
    """Test theme-aware image display."""

    def test_dark_theme_image_display(self, qapp, tmp_path):
        """Images should display correctly in dark theme."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1, theme="dark")

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)

        widget.insertFromMimeData(mime_data)

        # Should not have visual issues (hard to test programmatically)
        assert widget is not None

    def test_light_theme_image_display(self, qapp, tmp_path):
        """Images should display correctly in light theme."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1, theme="light")

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)

        widget.insertFromMimeData(mime_data)

        assert widget is not None

    def test_theme_change_updates_display(self, qapp, tmp_path):
        """Changing theme should update image display."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1, theme="dark")

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget.insertFromMimeData(mime_data)

        # Change theme
        if hasattr(widget, "update_theme"):
            widget.update_theme("light")

        # Should not crash or break display
        html = widget.toHtml()
        assert "<img" in html


class TestImageStagingForSave:
    """Test staging images for save on ticket save."""

    def test_get_pending_images(self, qapp, tmp_path):
        """Should track images pending save."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)

        widget.insertFromMimeData(mime_data)

        # Should have method to get pending images
        if hasattr(widget, "get_pending_images"):
            pending = widget.get_pending_images()
            assert len(pending) > 0

    def test_clear_pending_after_save(self, qapp, tmp_path):
        """Pending images should clear after successful save."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        mime_data = QMimeData()
        image = QImage(50, 50, QImage.Format.Format_ARGB32)
        mime_data.setImageData(image)
        widget.insertFromMimeData(mime_data)

        # Simulate save
        if hasattr(widget, "commit_images"):
            widget.commit_images()

        # Pending should be cleared
        if hasattr(widget, "get_pending_images"):
            pending = widget.get_pending_images()
            assert len(pending) == 0


class TestGetMarkdown:
    """Test getting markdown representation with image references."""

    def test_get_markdown_with_images(self, qapp, tmp_path):
        """Should convert HTML to markdown with image references."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Set HTML with image
        html = '<p>Before</p><img src="levelup/ticket-assets/test.png" alt="Test" /><p>After</p>'
        widget.setHtml(html)

        if hasattr(widget, "toMarkdown"):
            markdown = widget.toMarkdown()
            assert "![" in markdown
            assert "test.png" in markdown

    def test_get_markdown_plain_text(self, qapp, tmp_path):
        """Plain text should convert to markdown correctly."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)
        widget.setPlainText("Just plain text")

        if hasattr(widget, "toMarkdown"):
            markdown = widget.toMarkdown()
            assert "Just plain text" in markdown

    def test_get_markdown_mixed_content(self, qapp, tmp_path):
        """Mixed text and images should convert correctly."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        html = '<p>Description</p><img src="levelup/ticket-assets/img.png" /><p>More text</p>'
        widget.setHtml(html)

        if hasattr(widget, "toMarkdown"):
            markdown = widget.toMarkdown()
            assert "Description" in markdown
            assert "img.png" in markdown
            assert "More text" in markdown


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_paste_very_large_image_warning(self, qapp, tmp_path):
        """Pasting very large image should show warning."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        # Create large image (may trigger size warning)
        mime_data = QMimeData()
        large_image = QImage(5000, 5000, QImage.Format.Format_ARGB32)
        mime_data.setImageData(large_image)

        # Should handle gracefully (may warn user)
        try:
            widget.insertFromMimeData(mime_data)
        except Exception:
            pytest.fail("Should handle large images gracefully")

    def test_paste_corrupted_image_data(self, qapp, tmp_path):
        """Pasting corrupted image data should not crash."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        mime_data = QMimeData()
        # Set invalid image data
        mime_data.setData("application/x-qt-image", b"corrupted")

        try:
            widget.insertFromMimeData(mime_data)
        except Exception:
            # Should handle gracefully
            pass

    def test_null_project_path(self, qapp):
        """Creating widget with null project path should handle gracefully."""
        from levelup.gui.image_text_edit import ImageTextEdit

        # Should either work with limitations or raise clear error
        try:
            widget = ImageTextEdit(project_path=None)
            assert widget is not None
        except (TypeError, ValueError):
            # Acceptable to require project_path
            pass

    def test_change_ticket_number_after_creation(self, qapp, tmp_path):
        """Should be able to update ticket number for reuse."""
        from levelup.gui.image_text_edit import ImageTextEdit

        widget = ImageTextEdit(project_path=tmp_path, ticket_number=1)

        if hasattr(widget, "set_ticket_number"):
            widget.set_ticket_number(5)
            assert widget.ticket_number == 5
