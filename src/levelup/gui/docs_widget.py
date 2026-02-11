"""Documentation viewer widget for the GUI dashboard."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

# Directories to skip when discovering markdown files
_EXCLUDED_DIRS = {".venv", ".git", "node_modules", "__pycache__", ".pytest_cache"}

# Theme CSS templates for the rendered HTML document
_DARK_CSS = """
body { color: #CDD6F4; background: #181825; font-family: -apple-system, "Segoe UI", sans-serif; padding: 16px; line-height: 1.6; }
h1, h2, h3, h4, h5, h6 { color: #89B4FA; }
a { color: #89B4FA; }
code { background: #313244; color: #A6E3A1; padding: 2px 6px; border-radius: 3px; font-family: Consolas, monospace; }
pre { background: #313244; color: #A6E3A1; padding: 12px; border-radius: 6px; overflow-x: auto; }
pre code { background: transparent; padding: 0; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #45475A; padding: 8px; text-align: left; }
th { background: #313244; }
blockquote { border-left: 4px solid #45475A; margin-left: 0; padding-left: 12px; color: #A6ADC8; }
hr { border: none; border-top: 1px solid #45475A; }
"""

_LIGHT_CSS = """
body { color: #2E3440; background: #FFFFFF; font-family: -apple-system, "Segoe UI", sans-serif; padding: 16px; line-height: 1.6; }
h1, h2, h3, h4, h5, h6 { color: #5E81AC; }
a { color: #5E81AC; }
code { background: #E5E9F0; color: #BF616A; padding: 2px 6px; border-radius: 3px; font-family: Consolas, monospace; }
pre { background: #E5E9F0; color: #BF616A; padding: 12px; border-radius: 6px; overflow-x: auto; }
pre code { background: transparent; padding: 0; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #D8DEE9; padding: 8px; text-align: left; }
th { background: #E5E9F0; }
blockquote { border-left: 4px solid #D8DEE9; margin-left: 0; padding-left: 12px; color: #4C566A; }
hr { border: none; border-top: 1px solid #D8DEE9; }
"""


def render_markdown(text: str) -> str:
    """Convert markdown text to HTML body. Falls back to escaped plaintext."""
    try:
        import mistune

        md = mistune.create_markdown(plugins=["table", "strikethrough"])
        return md(text)  # type: ignore[return-value]
    except ImportError:
        # Graceful fallback: show raw text in a <pre> block
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"<pre>{escaped}</pre>"


def _wrap_html(body: str, theme: str = "dark") -> str:
    """Wrap an HTML body fragment in a full document with theme CSS."""
    css = _DARK_CSS if theme == "dark" else _LIGHT_CSS
    return f"<!DOCTYPE html><html><head><style>{css}</style></head><body>{body}</body></html>"


class DocsWidget(QWidget):
    """Widget for browsing and rendering project documentation files."""

    back_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project_path: Path | None = None
        self._files: list[Path] = []
        self._theme = "dark"

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Top bar: back button + file selector
        top_bar = QHBoxLayout()

        self._back_btn = QPushButton("\u2190 Back")
        self._back_btn.setObjectName("backBtn")
        self._back_btn.clicked.connect(self.back_clicked.emit)
        top_bar.addWidget(self._back_btn)

        self._file_selector = QComboBox()
        self._file_selector.setObjectName("docsFileSelector")
        self._file_selector.currentIndexChanged.connect(self._on_file_selected)
        top_bar.addWidget(self._file_selector, stretch=1)

        layout.addLayout(top_bar)

        # Body: rendered markdown browser
        self._browser = QTextBrowser()
        self._browser.setObjectName("docsBrowser")
        self._browser.setOpenLinks(False)
        self._browser.anchorClicked.connect(self._on_link_clicked)
        layout.addWidget(self._browser)

    def set_project_path(self, path: Path | None) -> None:
        """Discover markdown files and populate the dropdown."""
        self._project_path = path
        self._files.clear()
        self._file_selector.blockSignals(True)
        self._file_selector.clear()

        if path is None or not path.is_dir():
            self._file_selector.blockSignals(False)
            self._browser.setHtml(_wrap_html("<p>No project selected.</p>", self._theme))
            return

        # Discover .md files in root and levelup/ subdirectory
        md_files: list[Path] = []
        for f in sorted(path.iterdir()):
            if f.is_file() and f.suffix.lower() == ".md":
                md_files.append(f)

        levelup_dir = path / "levelup"
        if levelup_dir.is_dir():
            for f in sorted(levelup_dir.iterdir()):
                if f.is_file() and f.suffix.lower() == ".md":
                    md_files.append(f)

        # Filter out files inside excluded directories
        filtered: list[Path] = []
        for f in md_files:
            parts = f.relative_to(path).parts
            if not any(p in _EXCLUDED_DIRS for p in parts):
                filtered.append(f)

        self._files = filtered

        for f in self._files:
            rel = f.relative_to(path)
            self._file_selector.addItem(str(rel).replace("\\", "/"), str(f))

        self._file_selector.blockSignals(False)

        if self._files:
            self._file_selector.setCurrentIndex(0)
            self._on_file_selected(0)
        else:
            self._browser.setHtml(
                _wrap_html("<p>No markdown files found.</p>", self._theme)
            )

    def _on_file_selected(self, index: int) -> None:
        """Read and render the selected markdown file."""
        if index < 0 or index >= len(self._files):
            return

        file_path = self._files[index]
        try:
            text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = f"*Error reading {file_path.name}*"

        body = render_markdown(text)
        self._browser.setHtml(_wrap_html(body, self._theme))

    def _on_link_clicked(self, url: QUrl) -> None:
        """Handle link clicks in the browser."""
        scheme = url.scheme()
        if scheme in ("http", "https"):
            QDesktopServices.openUrl(url)
        elif url.hasFragment():
            self._browser.scrollToAnchor(url.fragment())

    def update_theme(self, theme: str) -> None:
        """Re-render current content with new theme colors."""
        self._theme = theme
        # Re-render the currently selected file
        index = self._file_selector.currentIndex()
        if index >= 0 and index < len(self._files):
            self._on_file_selected(index)
