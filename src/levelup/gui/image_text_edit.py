"""QTextEdit with image paste/drop support for ticket descriptions."""

from __future__ import annotations

import io
import re
from pathlib import Path

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QImageReader, QKeyEvent, QTextCursor, QTextDocument
from PyQt6.QtWidgets import QTextEdit

from levelup.gui.image_asset_manager import (
    get_image_extension,
    normalize_image_path,
    save_image,
    validate_image_size,
)


class ImageTextEdit(QTextEdit):
    """QTextEdit with image paste and drag-drop support.

    Features:
    - Paste/drop images directly into text
    - Tab/Shift-Tab trigger focus navigation instead of inserting tab characters
    - Enter emits save_requested signal instead of inserting newline
    - Shift-Enter inserts newline (normal behavior)
    """

    save_requested = pyqtSignal()

    def __init__(
        self,
        parent=None,
        project_path: Path | str | None = None,
        ticket_number: int | None = None,
        theme: str = "dark"
    ):
        super().__init__(parent)
        self.project_path = Path(project_path) if project_path else None
        self.ticket_number = ticket_number
        self._theme = theme
        self._pending_images: list[tuple[str, bytes, str]] = []  # [(temp_id, data, extension)]

        # Accept rich text
        self.setAcceptRichText(True)

    def set_ticket_number(self, ticket_number: int) -> None:
        """Update ticket number for image filenames."""
        self.ticket_number = ticket_number

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Override key press handling for keyboard navigation and save shortcuts."""
        key = event.key()
        modifiers = event.modifiers()

        # Handle Tab - trigger focus next
        if key == Qt.Key.Key_Tab and modifiers == Qt.KeyboardModifier.NoModifier:
            self.focusNextChild()
            event.accept()
            return

        # Handle Shift+Tab - trigger focus previous
        if key == Qt.Key.Key_Tab and modifiers == Qt.KeyboardModifier.ShiftModifier:
            self.focusPreviousChild()
            event.accept()
            return

        # Handle Enter (without modifiers) - emit save signal
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and modifiers == Qt.KeyboardModifier.NoModifier:
            self.save_requested.emit()
            event.accept()
            return

        # Handle Shift+Enter - insert newline (allow default behavior)
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and modifiers == Qt.KeyboardModifier.ShiftModifier:
            super().keyPressEvent(event)
            return

        # All other keys: default behavior
        super().keyPressEvent(event)

    def insertFromMimeData(self, source):
        """Override to handle image paste and drop."""
        # Check for image data
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage) and not image.isNull():
                self._insert_image(image)
                return

        # Check for URLs (file drops)
        if source.hasUrls():
            for url in source.urls():
                if url.isLocalFile():
                    filepath = url.toLocalFile()
                    # Check if it's an image file
                    if self._is_image_file(filepath):
                        self._insert_image_from_file(filepath)
            return

        # Handle text normally
        if source.hasText():
            super().insertFromMimeData(source)

    def _is_image_file(self, filepath: str) -> bool:
        """Check if file is an image based on extension."""
        ext = Path(filepath).suffix.lower()
        return ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp"}

    def _insert_image(self, image: QImage) -> None:
        """Insert pasted QImage."""
        if not self.project_path or self.ticket_number is None:
            # Can't save without project path and ticket number
            # Just insert as data URI
            self._insert_image_data_uri(image)
            return

        # Convert QImage to bytes
        buffer = QByteArray()
        qbuffer = QBuffer(buffer)
        qbuffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(qbuffer, "PNG")
        image_data = buffer.data()

        # Validate size
        if not validate_image_size(image_data):
            # Too large, skip or warn
            return

        # Generate temp ID for staging
        temp_id = f"temp-{len(self._pending_images)}"
        self._pending_images.append((temp_id, image_data, "png"))

        # Insert with temp path (will be replaced on save)
        cursor = self.textCursor()
        # Use a temporary src that will be replaced
        html = f'<img src="pending:{temp_id}" data-pending="{temp_id}" />'
        cursor.insertHtml(html)

    def _insert_image_data_uri(self, image: QImage) -> None:
        """Insert image as data URI (fallback when no project path)."""
        buffer = QByteArray()
        qbuffer = QBuffer(buffer)
        qbuffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(qbuffer, "PNG")

        # Convert to base64 data URI
        import base64
        b64_data = base64.b64encode(buffer.data()).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64_data}"

        cursor = self.textCursor()
        cursor.insertHtml(f'<img src="{data_uri}" />')

    def _insert_image_from_file(self, filepath: str) -> None:
        """Insert image from file path."""
        try:
            path = Path(filepath)
            image_data = path.read_bytes()

            if not validate_image_size(image_data):
                return

            # Determine extension
            extension = path.suffix.lstrip(".").lower()
            if not extension:
                extension = get_image_extension(image_data) or "png"

            if not self.project_path or self.ticket_number is None:
                # Load as QImage and insert as data URI
                image = QImage(filepath)
                if not image.isNull():
                    self._insert_image_data_uri(image)
                return

            # Stage for saving
            temp_id = f"temp-{len(self._pending_images)}"
            self._pending_images.append((temp_id, image_data, extension))

            cursor = self.textCursor()
            html = f'<img src="pending:{temp_id}" data-pending="{temp_id}" />'
            cursor.insertHtml(html)

        except Exception:
            # Failed to load image, ignore
            pass

    def get_pending_images(self) -> list[tuple[str, bytes, str]]:
        """Get list of pending images to be saved."""
        return self._pending_images.copy()

    def commit_images(self) -> None:
        """Commit pending images (called after successful save)."""
        self._pending_images.clear()

    def toMarkdown(self) -> str:
        """
        Convert HTML content to Markdown with image references.

        Returns:
            Markdown string
        """
        html = self.toHtml()
        return self._html_to_markdown(html)

    def setMarkdown(self, markdown: str) -> None:
        """
        Set content from Markdown (with image references).

        Args:
            markdown: Markdown string with image syntax
        """
        html = self._markdown_to_html(markdown)
        self.setHtml(html)

    def _html_to_markdown(self, html: str) -> str:
        """
        Convert HTML to Markdown.
        Simple conversion focusing on images and basic formatting.
        """
        # Extract plain text from HTML for base content
        doc = QTextDocument()
        doc.setHtml(html)
        text = doc.toPlainText()

        # Find images in HTML and replace with markdown syntax
        # Match: <img src="..." alt="..." /> or <img src="..." />
        img_pattern = re.compile(r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>', re.IGNORECASE)
        img_pattern_no_alt = re.compile(r'<img[^>]*src="([^"]*)"[^>]*/?>', re.IGNORECASE)

        markdown_lines = []

        # Parse HTML line by line (simplified approach)
        # For each image tag, create markdown image syntax
        lines = html.split('\n')
        for line in lines:
            # Find images with alt text
            for match in img_pattern.finditer(line):
                src = match.group(1)
                alt = match.group(2)
                # Skip pending images (they'll be replaced on save)
                if not src.startswith("pending:") and not src.startswith("data:"):
                    markdown_lines.append(f"![{alt}]({src})")

            # Find images without alt text
            for match in img_pattern_no_alt.finditer(line):
                src = match.group(1)
                # Check if already matched with alt
                if not img_pattern.search(line):
                    if not src.startswith("pending:") and not src.startswith("data:"):
                        markdown_lines.append(f"![]({src})")

        # Combine text and images (simplified - just append images)
        # For a better conversion, we'd need to parse HTML structure
        if markdown_lines:
            # Insert images at appropriate positions in text
            # For now, simple approach: preserve text and append images
            result = text
            for img_md in markdown_lines:
                if img_md not in result:
                    result += f"\n{img_md}"
            return result

        return text

    def _markdown_to_html(self, markdown: str) -> str:
        """
        Convert Markdown to HTML.
        Handles image syntax and preserves text.
        """
        if not markdown:
            return ""

        # Convert markdown images to HTML img tags
        # Pattern: ![alt text](image/path.png)
        def replace_image(match):
            alt_text = match.group(1)
            img_path = match.group(2)

            # Resolve path if project_path is available
            if self.project_path:
                full_path = self.project_path / img_path
                if full_path.exists():
                    # Use absolute file path for QTextEdit
                    img_path = str(full_path)

            return f'<img src="{img_path}" alt="{alt_text}" style="max-width: 100%;" />'

        # Replace markdown images
        html = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_image, markdown)

        # Convert newlines to HTML breaks
        html = html.replace('\n', '<br />')

        # Wrap in paragraph
        html = f"<p>{html}</p>"

        return html

    def update_theme(self, theme: str) -> None:
        """Update theme (for consistency with other widgets)."""
        self._theme = theme
        # Theme changes handled by parent stylesheet


def html_to_markdown(html: str, project_path: Path | str | None = None) -> str:
    """
    Convert HTML to Markdown (standalone utility).

    Args:
        html: HTML string
        project_path: Project path for resolving image paths

    Returns:
        Markdown string
    """
    # Create temporary widget for conversion
    widget = ImageTextEdit(project_path=project_path)
    widget.setHtml(html)
    return widget.toMarkdown()


def markdown_to_html(markdown: str, project_path: Path | str | None = None) -> str:
    """
    Convert Markdown to HTML (standalone utility).

    Args:
        markdown: Markdown string
        project_path: Project path for resolving image paths

    Returns:
        HTML string
    """
    # Create temporary widget for conversion
    widget = ImageTextEdit(project_path=project_path)
    widget.setMarkdown(markdown)
    return widget.toHtml()
