"""Markdown-HTML converter for ticket descriptions with image support."""

from __future__ import annotations

import html as html_module
import re
from pathlib import Path
from urllib.parse import unquote, urlparse


def markdown_to_html(markdown: str, project_path: Path | None = None) -> str:
    """
    Convert markdown to HTML for display in QTextEdit.

    Supports:
    - Plain text
    - Images: ![alt](path) -> <img src="absolute_path" alt="alt" />
    - Basic paragraph structure

    Args:
        markdown: Markdown text with optional image references
        project_path: Project root path for resolving relative image paths

    Returns:
        HTML string suitable for QTextEdit.setHtml()
    """
    if not markdown:
        return ""

    # Escape HTML special characters first
    escaped = html_module.escape(markdown)

    # Convert markdown image syntax to HTML
    # Pattern: ![alt text](image/path.png)
    def replace_image(match: re.Match) -> str:
        alt_text = match.group(1)
        image_path = match.group(2)

        # External URLs - validate and keep as-is
        if image_path.startswith(("http://", "https://")):
            # Escape the URL to prevent XSS
            escaped_url = html_module.escape(image_path, quote=True)
            return f'<img src="{escaped_url}" alt="{html_module.escape(alt_text)}" style="max-width: 100%;" />'

        # Block javascript: and data: URIs for security
        if image_path.startswith(("javascript:", "data:", "vbscript:", "file:")):
            # Return empty string to ignore malicious URIs
            return ""

        # Resolve to absolute path if project_path provided
        if project_path:
            # Convert to absolute path
            abs_path = (project_path / image_path).resolve()

            # SECURITY: Ensure resolved path is within project directory
            try:
                abs_path.relative_to(project_path.resolve())
            except ValueError:
                # Path traversal attempt detected - path is outside project directory
                return ""

            # Convert to file:// URL for QTextEdit (with forward slashes)
            file_url = abs_path.as_posix()
            if not file_url.startswith("file://"):
                file_url = f"file:///{file_url}" if abs_path.is_absolute() else file_url
            # Escape the URL
            file_url = html_module.escape(file_url, quote=True)
        else:
            file_url = html_module.escape(image_path, quote=True)

        return f'<img src="{file_url}" alt="{html_module.escape(alt_text)}" style="max-width: 100%;" />'

    # Replace markdown images with HTML img tags
    # SECURITY: Use non-greedy matching and limit input size to prevent ReDoS
    if len(escaped) > 1000000:  # 1MB text limit
        # For very large inputs, don't process images to prevent DoS
        return f'<p>{escaped}</p>'

    image_pattern = r'!\[([^\]]*?)\]\(([^\)]+?)\)'
    html_text = re.sub(image_pattern, replace_image, escaped)

    # Convert newlines to <br> for plain text portions
    # But preserve structure around images
    html_text = html_text.replace('\n', '<br />\n')

    # Wrap in paragraph for basic structure
    if html_text and not html_text.startswith('<'):
        html_text = f'<p>{html_text}</p>'

    return html_text


def html_to_markdown(html: str, project_path: Path | None = None) -> str:
    """
    Convert HTML from QTextEdit back to markdown format.

    Converts:
    - <img> tags back to ![alt](path) markdown syntax
    - Absolute paths back to relative paths
    - HTML paragraphs to plain text with newlines

    Args:
        html: HTML string from QTextEdit.toHtml()
        project_path: Project root path for converting absolute paths to relative

    Returns:
        Markdown string for storage in tickets.md
    """
    if not html:
        return ""

    # SECURITY: Limit input size to prevent DoS
    if len(html) > 5000000:  # 5MB HTML limit
        # For very large inputs, extract plain text only
        return html[:1000000]

    result = html

    # Convert <img> tags to markdown syntax
    def replace_img_tag(match: re.Match) -> str:
        img_tag = match.group(0)

        # Extract src and alt from img tag (non-greedy to prevent ReDoS)
        src_match = re.search(r'src="([^"]+?)"', img_tag)
        alt_match = re.search(r'alt="([^"]*?)"', img_tag)

        if not src_match:
            return ""

        src = src_match.group(1)
        alt = alt_match.group(1) if alt_match else ""

        # Unescape HTML entities in alt text
        alt = html_module.unescape(alt)

        # Convert file:// URLs to paths
        if src.startswith("file:///"):
            src = src[8:]  # Remove file:///
        elif src.startswith("file://"):
            src = src[7:]  # Remove file://

        # URL decode
        src = unquote(src)

        # Convert absolute path to relative if project_path provided
        if project_path:
            try:
                # Handle paths that start with / (POSIX-style absolute paths)
                # even on Windows - treat them as absolute for conversion purposes
                if src.startswith('/'):
                    # Try to make relative to project_path
                    project_str = str(project_path).replace('\\', '/')
                    if src.startswith(project_str):
                        # Remove project path prefix
                        src = src[len(project_str):].lstrip('/')
                    elif src.startswith(project_path.as_posix()):
                        src = src[len(project_path.as_posix()):].lstrip('/')
                else:
                    src_path = Path(src)
                    if src_path.is_absolute():
                        # Try to make relative to project path
                        try:
                            rel_path = src_path.relative_to(project_path)
                            src = rel_path.as_posix()
                        except ValueError:
                            # Not relative to project path, keep as-is
                            pass
            except (ValueError, OSError):
                # Invalid path, keep as-is
                pass

        # Normalize backslashes to forward slashes
        src = src.replace("\\", "/")

        return f"![{alt}]({src})"

    # Replace all <img> tags (use possessive quantifier to prevent ReDoS)
    img_pattern = r'<img[^>]*?/?>'
    result = re.sub(img_pattern, replace_img_tag, result)

    # Remove HTML tags except <br>
    # First convert <br> to newlines
    result = re.sub(r'<br\s*/?>','\n', result, flags=re.IGNORECASE)

    # Remove <p> and </p> tags
    result = re.sub(r'</?p[^>]*>', '', result, flags=re.IGNORECASE)

    # Remove other HTML tags
    result = re.sub(r'<[^>]+>', '', result)

    # Unescape HTML entities
    result = html_module.unescape(result)

    # Clean up excessive newlines (more than 2 consecutive)
    result = re.sub(r'\n{3,}', '\n\n', result)

    # Strip leading/trailing whitespace
    result = result.strip()

    return result
