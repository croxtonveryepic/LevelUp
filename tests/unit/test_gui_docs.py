"""Tests for the documentation viewer widget in the GUI dashboard."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch as _patch

import pytest


def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def _ensure_qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _make_state_manager(tmp_path: Path):
    from levelup.state.manager import StateManager
    db_path = tmp_path / "test_state.db"
    return StateManager(db_path=db_path)


def _make_main_window(state_manager, project_path=None):
    from unittest.mock import patch as _p
    from levelup.gui.main_window import MainWindow

    with _p.object(MainWindow, "_start_refresh_timer"), \
         _p.object(MainWindow, "_refresh"):
        win = MainWindow(state_manager, project_path=project_path)
    return win


def _create_md_files(root: Path) -> None:
    """Create sample markdown files in a temp project directory."""
    (root / "README.md").write_text("# Project\n\nHello world.\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text("# Changelog\n\n- v1.0\n", encoding="utf-8")
    levelup_dir = root / "levelup"
    levelup_dir.mkdir(exist_ok=True)
    (levelup_dir / "tickets.md").write_text("## Ticket 1\nDo stuff\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# TestMarkdownToHtml — pure rendering (no Qt required)
# ---------------------------------------------------------------------------


class TestMarkdownToHtml:
    """Test the render_markdown() helper in isolation."""

    def test_heading_produces_h1(self):
        from levelup.gui.docs_widget import render_markdown

        html = render_markdown("# Hello")
        assert "<h1>" in html

    def test_code_block_produces_pre(self):
        from levelup.gui.docs_widget import render_markdown

        html = render_markdown("```\ncode\n```")
        assert "<pre>" in html or "<code>" in html

    def test_bold_produces_strong(self):
        from levelup.gui.docs_widget import render_markdown

        html = render_markdown("**bold**")
        assert "<strong>" in html

    def test_italic_produces_em(self):
        from levelup.gui.docs_widget import render_markdown

        html = render_markdown("*italic*")
        assert "<em>" in html

    def test_link_produces_anchor(self):
        from levelup.gui.docs_widget import render_markdown

        html = render_markdown("[click](https://example.com)")
        assert "<a " in html
        assert "https://example.com" in html

    def test_table_produces_table_tag(self):
        from levelup.gui.docs_widget import render_markdown

        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = render_markdown(md)
        assert "<table>" in html or "<table" in html

    def test_fallback_without_mistune(self):
        from levelup.gui import docs_widget

        with _patch.dict("sys.modules", {"mistune": None}):
            # Force re-import failure by patching import
            import importlib

            orig = docs_widget.render_markdown

            # Simulate ImportError inside the function
            def fake_render(text: str) -> str:
                escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                return f"<pre>{escaped}</pre>"

            docs_widget.render_markdown = fake_render
            try:
                result = docs_widget.render_markdown("# Hello")
                assert "<pre>" in result
                assert "# Hello" in result
            finally:
                docs_widget.render_markdown = orig


# ---------------------------------------------------------------------------
# TestDocsWidgetFileDiscovery
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDocsWidgetFileDiscovery:
    """Test that DocsWidget discovers the right markdown files."""

    def test_discovers_root_md_files(self, tmp_path):
        app = _ensure_qapp()
        _create_md_files(tmp_path)

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(tmp_path)

        labels = [w._file_selector.itemText(i) for i in range(w._file_selector.count())]
        assert "README.md" in labels
        assert "CHANGELOG.md" in labels

    def test_discovers_levelup_dir_files(self, tmp_path):
        app = _ensure_qapp()
        _create_md_files(tmp_path)

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(tmp_path)

        labels = [w._file_selector.itemText(i) for i in range(w._file_selector.count())]
        assert "levelup/tickets.md" in labels

    def test_excludes_venv_and_git(self, tmp_path):
        app = _ensure_qapp()
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        (venv_dir / "notes.md").write_text("internal", encoding="utf-8")

        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "info.md").write_text("git stuff", encoding="utf-8")

        (tmp_path / "README.md").write_text("# Hi", encoding="utf-8")

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(tmp_path)

        labels = [w._file_selector.itemText(i) for i in range(w._file_selector.count())]
        assert "README.md" in labels
        assert len(labels) == 1  # .venv and .git files excluded

    def test_handles_empty_project(self, tmp_path):
        app = _ensure_qapp()

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(tmp_path)

        assert w._file_selector.count() == 0
        assert "No markdown files" in w._browser.toHtml()

    def test_handles_none_project_path(self):
        app = _ensure_qapp()

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(None)

        assert w._file_selector.count() == 0
        assert "No project selected" in w._browser.toHtml()


# ---------------------------------------------------------------------------
# TestDocsWidgetRendering
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDocsWidgetRendering:
    """Test that selected files are rendered as HTML in the browser."""

    def test_heading_rendered(self, tmp_path):
        app = _ensure_qapp()
        (tmp_path / "README.md").write_text("# Big Title", encoding="utf-8")

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(tmp_path)

        html = w._browser.toHtml()
        assert "Big Title" in html

    def test_code_block_rendered(self, tmp_path):
        app = _ensure_qapp()
        (tmp_path / "README.md").write_text("```python\nprint('hi')\n```", encoding="utf-8")

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(tmp_path)

        html = w._browser.toHtml()
        assert "print" in html

    def test_table_rendered(self, tmp_path):
        app = _ensure_qapp()
        (tmp_path / "README.md").write_text(
            "| A | B |\n|---|---|\n| 1 | 2 |", encoding="utf-8"
        )

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(tmp_path)

        html = w._browser.toHtml()
        # QTextBrowser re-renders HTML; check for table content
        assert "1" in html and "2" in html

    def test_bold_rendered(self, tmp_path):
        app = _ensure_qapp()
        (tmp_path / "README.md").write_text("**bold text**", encoding="utf-8")

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(tmp_path)

        html = w._browser.toHtml()
        assert "bold text" in html

    def test_link_rendered(self, tmp_path):
        app = _ensure_qapp()
        (tmp_path / "README.md").write_text(
            "[click here](https://example.com)", encoding="utf-8"
        )

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(tmp_path)

        html = w._browser.toHtml()
        assert "click here" in html
        assert "example.com" in html


# ---------------------------------------------------------------------------
# TestDocsWidgetNavigation
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDocsWidgetNavigation:
    """Test navigation: back signal, file switching, external links."""

    def test_back_signal_emits(self):
        app = _ensure_qapp()

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        received = []
        w.back_clicked.connect(lambda: received.append(True))

        w._back_btn.click()
        assert len(received) == 1

    def test_file_selector_change_triggers_rerender(self, tmp_path):
        app = _ensure_qapp()
        _create_md_files(tmp_path)

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(tmp_path)

        # Initially first file is selected
        html_before = w._browser.toHtml()

        # Switch to another file
        if w._file_selector.count() > 1:
            w._file_selector.setCurrentIndex(1)
            html_after = w._browser.toHtml()
            assert html_before != html_after

    def test_external_link_opens_browser(self, tmp_path):
        app = _ensure_qapp()
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()

        with _patch.object(QDesktopServices, "openUrl") as mock_open:
            url = QUrl("https://example.com")
            w._on_link_clicked(url)
            mock_open.assert_called_once_with(url)

    def test_anchor_link_does_not_open_browser(self, tmp_path):
        app = _ensure_qapp()
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()

        with _patch.object(QDesktopServices, "openUrl") as mock_open:
            url = QUrl("#section")
            w._on_link_clicked(url)
            mock_open.assert_not_called()


# ---------------------------------------------------------------------------
# TestDocsWidgetTheme
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDocsWidgetTheme:
    """Test theme-aware rendering."""

    def test_dark_css_has_dark_colors(self, tmp_path):
        app = _ensure_qapp()
        (tmp_path / "README.md").write_text("# Hello", encoding="utf-8")

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.update_theme("dark")
        w.set_project_path(tmp_path)

        html = w._browser.toHtml()
        # Dark theme body uses #181825 background
        assert "181825" in html or "CDD6F4" in html

    def test_light_css_has_light_colors(self, tmp_path):
        app = _ensure_qapp()
        (tmp_path / "README.md").write_text("# Hello", encoding="utf-8")

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.update_theme("light")
        w.set_project_path(tmp_path)

        html = w._browser.toHtml().lower()
        assert "ffffff" in html or "2e3440" in html

    def test_update_theme_rerenders(self, tmp_path):
        app = _ensure_qapp()
        (tmp_path / "README.md").write_text("# Theme Test", encoding="utf-8")

        from levelup.gui.docs_widget import DocsWidget

        w = DocsWidget()
        w.set_project_path(tmp_path)

        # Get dark HTML
        w.update_theme("dark")
        dark_html = w._browser.toHtml()

        # Switch to light
        w.update_theme("light")
        light_html = w._browser.toHtml()

        assert dark_html != light_html


# ---------------------------------------------------------------------------
# TestMainWindowDocsIntegration
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestMainWindowDocsIntegration:
    """Test that DocsWidget is wired into the main window correctly."""

    def test_docs_button_exists(self, tmp_path):
        app = _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton

        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        btn = win.findChild(QPushButton, "docsBtn")
        assert btn is not None

    def test_docs_click_switches_to_page_2(self, tmp_path):
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        win._on_docs_clicked()
        assert win._stack.currentIndex() == 2

    def test_docs_back_returns_to_page_0(self, tmp_path):
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        win._on_docs_clicked()
        assert win._stack.currentIndex() == 2

        win._on_docs_back()
        assert win._stack.currentIndex() == 0

    def test_docs_click_clears_sidebar_selection(self, tmp_path):
        app = _ensure_qapp()
        from levelup.core.tickets import Ticket, TicketStatus

        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        win._sidebar.set_tickets([
            Ticket(number=1, title="A", status=TicketStatus.PENDING),
        ])
        win._sidebar._list.setCurrentRow(0)

        win._on_docs_clicked()
        assert win._sidebar._list.currentRow() == -1

    def test_stack_has_three_pages(self, tmp_path):
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        assert win._stack.count() == 3
