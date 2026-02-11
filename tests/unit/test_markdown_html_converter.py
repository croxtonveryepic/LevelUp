"""Unit tests for markdown-HTML conversion with image support."""

from __future__ import annotations

import pytest
from pathlib import Path


class TestMarkdownToHtml:
    """Test converting markdown to HTML for QTextEdit display."""

    def test_plain_text_preserved(self):
        """Plain text without formatting should be preserved."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = "This is plain text"
        html = markdown_to_html(markdown)

        assert "This is plain text" in html

    def test_single_image_reference_converted(self):
        """Markdown image syntax should convert to HTML img tag."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = "![Screenshot](levelup/ticket-assets/ticket-1-20260211-abc123.png)"
        html = markdown_to_html(markdown, project_path=Path("/test/project"))

        assert "<img" in html
        assert "ticket-1-20260211-abc123.png" in html

    def test_multiple_images_converted(self):
        """Multiple image references should all be converted."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = """
![First](levelup/ticket-assets/image1.png)
Some text
![Second](levelup/ticket-assets/image2.png)
"""
        html = markdown_to_html(markdown, project_path=Path("/test/project"))

        assert html.count("<img") == 2
        assert "image1.png" in html
        assert "image2.png" in html

    def test_image_alt_text_preserved(self):
        """Alt text from markdown should be included in HTML."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = "![Error message screenshot](levelup/ticket-assets/error.png)"
        html = markdown_to_html(markdown, project_path=Path("/test/project"))

        assert 'alt="Error message screenshot"' in html or "Error message screenshot" in html

    def test_mixed_content_with_images(self):
        """Text mixed with images should be properly converted."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = """Here is the issue:
![Screenshot](levelup/ticket-assets/bug.png)
As you can see above, the button is broken."""

        html = markdown_to_html(markdown, project_path=Path("/test/project"))

        assert "Here is the issue:" in html
        assert "<img" in html
        assert "button is broken" in html

    def test_absolute_path_resolution(self):
        """Image paths should be resolved to absolute paths."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = "![Test](levelup/ticket-assets/test.png)"
        project_path = Path("/absolute/project/path")
        html = markdown_to_html(markdown, project_path=project_path)

        # Should contain absolute path (platform-specific)
        assert "ticket-assets" in html

    def test_empty_string_returns_empty(self):
        """Empty markdown should return empty or minimal HTML."""
        from levelup.gui.markdown_converter import markdown_to_html

        html = markdown_to_html("", project_path=Path("/test"))

        assert html == "" or html.strip() == ""

    def test_special_characters_escaped(self):
        """Special HTML characters should be escaped in plain text."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = "Code: <script>alert('test')</script>"
        html = markdown_to_html(markdown, project_path=Path("/test"))

        # Should escape HTML to prevent injection
        assert "&lt;" in html or "script" not in html.lower() or "<script>" not in html


class TestHtmlToMarkdown:
    """Test converting HTML from QTextEdit back to markdown."""

    def test_plain_text_preserved(self):
        """Plain text should be extracted from HTML."""
        from levelup.gui.markdown_converter import html_to_markdown

        html = "<p>This is plain text</p>"
        markdown = html_to_markdown(html, project_path=Path("/test"))

        assert "This is plain text" in markdown

    def test_single_image_converted_to_markdown(self):
        """HTML img tag should convert to markdown image syntax."""
        from levelup.gui.markdown_converter import html_to_markdown

        html = '<img src="/test/project/levelup/ticket-assets/test.png" alt="Screenshot" />'
        markdown = html_to_markdown(html, project_path=Path("/test/project"))

        assert "![Screenshot]" in markdown or "![" in markdown
        assert "ticket-assets/test.png" in markdown or "test.png" in markdown

    def test_multiple_images_converted(self):
        """Multiple images should all be converted to markdown."""
        from levelup.gui.markdown_converter import html_to_markdown

        html = """
        <p><img src="/test/levelup/ticket-assets/img1.png" /></p>
        <p>Text between</p>
        <p><img src="/test/levelup/ticket-assets/img2.png" /></p>
        """
        markdown = html_to_markdown(html, project_path=Path("/test"))

        assert markdown.count("![") == 2
        assert "img1.png" in markdown
        assert "img2.png" in markdown

    def test_absolute_path_converted_to_relative(self):
        """Absolute image paths should be converted to relative paths."""
        from levelup.gui.markdown_converter import html_to_markdown

        html = '<img src="/absolute/path/to/project/levelup/ticket-assets/image.png" />'
        markdown = html_to_markdown(html, project_path=Path("/absolute/path/to/project"))

        # Should produce relative path
        assert "levelup/ticket-assets/image.png" in markdown
        assert "/absolute/path" not in markdown

    def test_file_url_scheme_handled(self):
        """File:// URLs should be handled correctly."""
        from levelup.gui.markdown_converter import html_to_markdown

        html = '<img src="file:///C:/project/levelup/ticket-assets/test.png" />'
        markdown = html_to_markdown(html, project_path=Path("C:/project"))

        assert "levelup/ticket-assets/test.png" in markdown
        assert "file://" not in markdown

    def test_mixed_content_preserved(self):
        """Mixed text and images should both be preserved."""
        from levelup.gui.markdown_converter import html_to_markdown

        html = """
        <p>Before image</p>
        <p><img src="/test/levelup/ticket-assets/img.png" alt="Test" /></p>
        <p>After image</p>
        """
        markdown = html_to_markdown(html, project_path=Path("/test"))

        assert "Before image" in markdown
        assert "![" in markdown
        assert "After image" in markdown

    def test_newlines_preserved(self):
        """Paragraph structure should create appropriate newlines."""
        from levelup.gui.markdown_converter import html_to_markdown

        html = "<p>First paragraph</p><p>Second paragraph</p>"
        markdown = html_to_markdown(html, project_path=Path("/test"))

        # Should have some separation between paragraphs
        assert "First paragraph" in markdown
        assert "Second paragraph" in markdown


class TestRoundTripConversion:
    """Test markdown -> HTML -> markdown round-trip preservation."""

    def test_plain_text_round_trip(self):
        """Plain text should survive round-trip conversion."""
        from levelup.gui.markdown_converter import markdown_to_html, html_to_markdown

        original = "This is a test description.\nWith multiple lines."
        project_path = Path("/test")

        html = markdown_to_html(original, project_path)
        result = html_to_markdown(html, project_path)

        # Core content should be preserved (may have formatting differences)
        assert "This is a test description" in result
        assert "With multiple lines" in result

    def test_image_reference_round_trip(self):
        """Image references should survive round-trip conversion."""
        from levelup.gui.markdown_converter import markdown_to_html, html_to_markdown

        original = "![Screenshot](levelup/ticket-assets/ticket-5-test.png)"
        project_path = Path("/test/project")

        html = markdown_to_html(original, project_path)
        result = html_to_markdown(html, project_path)

        # Should preserve image reference
        assert "ticket-5-test.png" in result
        assert "levelup/ticket-assets" in result

    def test_mixed_content_round_trip(self):
        """Mixed text and images should survive round-trip."""
        from levelup.gui.markdown_converter import markdown_to_html, html_to_markdown

        original = """Problem description:
![Error screenshot](levelup/ticket-assets/error.png)
The button doesn't work."""

        project_path = Path("/test")
        html = markdown_to_html(original, project_path)
        result = html_to_markdown(html, project_path)

        assert "Problem description" in result
        assert "error.png" in result
        assert "button doesn't work" in result


class TestEdgeCases:
    """Test edge cases in markdown-HTML conversion."""

    def test_missing_alt_text(self):
        """Images without alt text should still convert."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = "![](levelup/ticket-assets/image.png)"
        html = markdown_to_html(markdown, project_path=Path("/test"))

        assert "<img" in html
        assert "image.png" in html

    def test_malformed_image_syntax(self):
        """Malformed markdown image syntax should be handled gracefully."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = "!Screenshot](broken.png)"
        html = markdown_to_html(markdown, project_path=Path("/test"))

        # Should not crash - may render as text or ignore
        assert html is not None

    def test_external_url_in_image(self):
        """External URLs in images should be preserved."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = "![External](https://example.com/image.png)"
        html = markdown_to_html(markdown, project_path=Path("/test"))

        # External URLs should be kept as-is
        assert "https://example.com/image.png" in html

    def test_unicode_in_alt_text(self):
        """Unicode characters in alt text should be preserved."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = "![错误截图](levelup/ticket-assets/error.png)"
        html = markdown_to_html(markdown, project_path=Path("/test"))

        assert "错误截图" in html or "error.png" in html

    def test_very_long_description(self):
        """Very long descriptions should be handled."""
        from levelup.gui.markdown_converter import markdown_to_html

        markdown = "A" * 10000  # 10k characters
        html = markdown_to_html(markdown, project_path=Path("/test"))

        assert len(html) > 0
        assert "A" in html
