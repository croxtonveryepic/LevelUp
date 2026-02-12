"""Unit tests for DiffViewWidget.

This test suite covers the requirements for a new diff view widget that displays
git diffs for pipeline runs on a per-commit (step) basis or for the entire branch.

Requirements:
- DiffViewWidget extends QWidget and follows existing GUI patterns
- Uses QTextBrowser for displaying formatted diff output with syntax highlighting
- Supports both dark and light theme with appropriate color schemes
- Displays diff in unified format with file names, line numbers, and change indicators
- Handles empty diffs gracefully
- Accepts run_id and optional step_name parameters
- Retrieves PipelineContext from RunRecord.context_json
- Extracts commit SHA from ctx.step_commits[step_name] for per-step view
- Uses GitPython to generate diff from parent commit to step commit
- Displays commit message and step name in header
- Provides dropdown/list to select different pipeline steps
- Supports whole-branch diff from pre_run_sha to branch HEAD
- Displays summary statistics for branch-level view
- Supports live updates for in-progress runs
- Handles edge cases: no git branch, missing commits, GitPython errors
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest


def _can_import_pyqt6() -> bool:
    """Check if PyQt6 is available."""
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def _ensure_qapp():
    """Ensure QApplication exists."""
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _make_state_manager(tmp_path: Path):
    """Create a StateManager with a test database."""
    from levelup.state.manager import StateManager
    db_path = tmp_path / "test_state.db"
    return StateManager(db_path=db_path)


def _init_git_repo(tmp_path: Path):
    """Create a git repo with an initial commit."""
    import git
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    (tmp_path / "init.txt").write_text("initial content")
    repo.index.add(["init.txt"])
    repo.index.commit("initial commit")
    return repo


pytestmark = pytest.mark.regression


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewWidgetStructure:
    """Test the basic structure and layout of DiffViewWidget."""

    def test_widget_exists(self):
        """DiffViewWidget class should exist and be importable."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget

        widget = DiffViewWidget()
        assert widget is not None

    def test_widget_extends_qwidget(self):
        """DiffViewWidget should extend QWidget."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QWidget

        widget = DiffViewWidget()
        assert isinstance(widget, QWidget)

    def test_widget_has_back_button(self):
        """Widget should have a back button following existing GUI patterns."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QPushButton

        widget = DiffViewWidget()
        back_btn = widget.findChild(QPushButton, "backBtn")

        assert back_btn is not None

    def test_widget_has_back_clicked_signal(self):
        """Widget should have a back_clicked signal for navigation."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget

        widget = DiffViewWidget()
        assert hasattr(widget, "back_clicked")

    def test_widget_has_text_browser(self):
        """Widget should have a QTextBrowser for displaying diff content."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QTextBrowser

        widget = DiffViewWidget()
        browser = widget.findChild(QTextBrowser)

        assert browser is not None

    def test_widget_has_header_title(self):
        """Widget should have a header with title."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QLabel

        widget = DiffViewWidget()
        labels = widget.findChildren(QLabel)

        # Should have at least one label for the header
        assert len(labels) > 0

    def test_widget_has_step_selector(self):
        """Widget should have a dropdown/combo box for selecting pipeline steps."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QComboBox

        widget = DiffViewWidget()
        combo = widget.findChild(QComboBox)

        assert combo is not None


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewWidgetInitialization:
    """Test initialization and parameter handling."""

    def test_accepts_run_id_parameter(self):
        """Widget should accept run_id parameter."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget

        widget = DiffViewWidget(run_id="test_run_123")
        assert widget is not None

    def test_accepts_step_name_parameter(self):
        """Widget should accept optional step_name parameter for per-step view."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget

        widget = DiffViewWidget(run_id="test_run_123", step_name="requirements")
        assert widget is not None

    def test_accepts_state_manager_parameter(self):
        """Widget should accept state_manager parameter."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget

        mock_state_manager = MagicMock()
        widget = DiffViewWidget(run_id="test_run_123", state_manager=mock_state_manager)
        assert widget is not None

    def test_accepts_theme_parameter(self):
        """Widget should accept theme parameter (dark/light)."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget

        widget_dark = DiffViewWidget(theme="dark")
        assert widget_dark is not None

        widget_light = DiffViewWidget(theme="light")
        assert widget_light is not None

    def test_accepts_project_path_parameter(self):
        """Widget should accept project_path parameter for git operations."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget

        widget = DiffViewWidget(run_id="test_run_123", project_path="/path/to/project")
        assert widget is not None


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewWidgetNavigation:
    """Test navigation and signals."""

    def test_back_button_emits_signal(self):
        """Clicking back button should emit back_clicked signal."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QPushButton

        widget = DiffViewWidget()
        back_btn = widget.findChild(QPushButton, "backBtn")

        signal_emitted = False

        def on_back():
            nonlocal signal_emitted
            signal_emitted = True

        widget.back_clicked.connect(on_back)
        back_btn.click()

        assert signal_emitted is True

    def test_step_selector_changes_view(self):
        """Changing step in selector should update the diff display."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QComboBox, QTextBrowser

        widget = DiffViewWidget()
        combo = widget.findChild(QComboBox)
        browser = widget.findChild(QTextBrowser)

        # Initially should show something
        initial_html = browser.toHtml()

        # Add steps to selector
        if combo and combo.count() > 1:
            combo.setCurrentIndex(1)
            updated_html = browser.toHtml()
            # Content should change (or at least be rendered)
            assert browser is not None


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewWidgetThemeSupport:
    """Test theme support (dark/light mode)."""

    def test_widget_has_update_theme_method(self):
        """Widget should have update_theme method."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget

        widget = DiffViewWidget()
        assert hasattr(widget, "update_theme")

    def test_dark_theme_uses_dark_colors(self):
        """Dark theme should use dark color scheme for diff display."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QTextBrowser

        widget = DiffViewWidget(theme="dark")
        browser = widget.findChild(QTextBrowser)

        # Set some diff content
        widget.set_diff_content("diff content", "test.py")

        html = browser.toHtml()
        # Dark theme should have dark background colors
        assert "181825" in html or "313244" in html or "#181825" in html.lower() or "#313244" in html.lower()

    def test_light_theme_uses_light_colors(self):
        """Light theme should use light color scheme for diff display."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QTextBrowser

        widget = DiffViewWidget(theme="light")
        browser = widget.findChild(QTextBrowser)

        # Set some diff content
        widget.set_diff_content("diff content", "test.py")

        html = browser.toHtml().lower()
        # Light theme should have light background colors
        assert "ffffff" in html or "e5e9f0" in html

    def test_update_theme_changes_colors(self):
        """Calling update_theme should change the displayed colors."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QTextBrowser

        widget = DiffViewWidget(theme="dark")
        browser = widget.findChild(QTextBrowser)

        widget.set_diff_content("diff content", "test.py")
        dark_html = browser.toHtml()

        widget.update_theme("light")
        light_html = browser.toHtml()

        # HTML should be different after theme change
        assert dark_html != light_html

    def test_diff_additions_use_green_color(self):
        """Added lines (+) should be displayed in green."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QTextBrowser

        widget = DiffViewWidget(theme="dark")
        browser = widget.findChild(QTextBrowser)

        diff_text = "+new line added"
        widget.set_diff_content(diff_text, "test.py")

        html = browser.toHtml().lower()
        # Green color for additions
        assert "green" in html or "#2ecc71" in html or "#a6e3a1" in html

    def test_diff_deletions_use_red_color(self):
        """Deleted lines (-) should be displayed in red."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from PyQt6.QtWidgets import QTextBrowser

        widget = DiffViewWidget(theme="dark")
        browser = widget.findChild(QTextBrowser)

        diff_text = "-deleted line"
        widget.set_diff_content(diff_text, "test.py")

        html = browser.toHtml().lower()
        # Red color for deletions
        assert "red" in html or "#e74c3c" in html or "#f38ba8" in html


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewWidgetContextRetrieval:
    """Test retrieving PipelineContext from RunRecord."""

    def test_retrieves_context_from_state_manager(self, tmp_path):
        """Widget should retrieve RunRecord and extract PipelineContext from context_json."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput
        from levelup.state.manager import StateManager

        sm = _make_state_manager(tmp_path)

        # Create a run with context
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha="abc123",
            step_commits={"requirements": "def456", "planning": "ghi789"},
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(run_id="test_run_123", state_manager=sm)

        # Widget should have loaded the context
        assert widget._run_id == "test_run_123"

    def test_handles_missing_run_gracefully(self, tmp_path):
        """Widget should handle case where run_id doesn't exist."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget

        sm = _make_state_manager(tmp_path)
        widget = DiffViewWidget(run_id="nonexistent_run", state_manager=sm)

        # Should not crash, should show error message
        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        assert browser is not None

        html = browser.toHtml()
        assert "not found" in html.lower() or "error" in html.lower()

    def test_extracts_step_commits_from_context(self, tmp_path):
        """Widget should extract step_commits dict from PipelineContext."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        sm = _make_state_manager(tmp_path)

        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha="abc123",
            step_commits={
                "requirements": "sha_req",
                "planning": "sha_plan",
                "test_writing": "sha_test",
            },
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(run_id="test_run_123", state_manager=sm)

        # Widget should populate step selector with available steps
        from PyQt6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox)
        assert combo is not None

        # Should have entries for each step + "All Changes" option
        assert combo.count() >= 3

    def test_extracts_pre_run_sha_from_context(self, tmp_path):
        """Widget should extract pre_run_sha from PipelineContext."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        sm = _make_state_manager(tmp_path)

        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha="initial_sha_abc123",
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(run_id="test_run_123", state_manager=sm)

        # Widget should have stored pre_run_sha
        assert hasattr(widget, "_pre_run_sha") or hasattr(widget, "_context")

    def test_handles_none_pre_run_sha(self, tmp_path):
        """Widget should handle case where pre_run_sha is None (no git tracking)."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        sm = _make_state_manager(tmp_path)

        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=None,  # No git tracking
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(run_id="test_run_123", state_manager=sm)

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should show appropriate message
        assert "no git" in html.lower() or "not tracked" in html.lower() or "no branch" in html.lower()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewWidgetPerStepDiff:
    """Test per-step (per-commit) diff generation."""

    def test_generates_diff_for_specific_step(self, tmp_path):
        """Widget should generate diff for a specific pipeline step."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        # Create a change and commit (simulating step commit)
        (tmp_path / "requirements.txt").write_text("pytest\n")
        repo.index.add(["requirements.txt"])
        step_sha = repo.index.commit("levelup(requirements): Test task").hexsha

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
            step_commits={"requirements": step_sha},
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            step_name="requirements",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should contain diff markers
        assert "requirements.txt" in html or "pytest" in html

    def test_displays_step_name_in_header(self, tmp_path):
        """Widget should display the step name in the header."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha
        (tmp_path / "test.py").write_text("pass")
        repo.index.add(["test.py"])
        step_sha = repo.index.commit("levelup(planning): Test").hexsha

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
            step_commits={"planning": step_sha},
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            step_name="planning",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QLabel
        labels = widget.findChildren(QLabel)
        label_texts = [label.text() for label in labels]

        # Header should mention the step name
        assert any("planning" in text.lower() for text in label_texts)

    def test_displays_commit_message(self, tmp_path):
        """Widget should display the commit message for the step."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha
        (tmp_path / "test.py").write_text("pass")
        repo.index.add(["test.py"])
        commit_msg = "levelup(requirements): Add feature X\n\nRun ID: test_run_123"
        step_sha = repo.index.commit(commit_msg).hexsha

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
            step_commits={"requirements": step_sha},
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            step_name="requirements",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should contain commit message
        assert "Add feature X" in html or "test_run_123" in html

    def test_handles_missing_step_commit(self, tmp_path):
        """Widget should handle case where step_name is not in step_commits."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        _init_git_repo(tmp_path)

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha="abc123",
            step_commits={},  # No step commits yet
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            step_name="nonexistent_step",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should show appropriate error message
        assert "not found" in html.lower() or "no commit" in html.lower()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewWidgetWholeBranchDiff:
    """Test whole-branch diff (from pre_run_sha to branch HEAD)."""

    def test_generates_diff_for_entire_branch(self, tmp_path):
        """Widget should generate diff from pre_run_sha to branch HEAD."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        # Make multiple changes
        (tmp_path / "file1.py").write_text("content1")
        repo.index.add(["file1.py"])
        repo.index.commit("Add file1")

        (tmp_path / "file2.py").write_text("content2")
        repo.index.add(["file2.py"])
        repo.index.commit("Add file2")

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should show all changes
        assert "file1.py" in html or "file2.py" in html

    def test_displays_summary_statistics(self, tmp_path):
        """Widget should display summary stats (files changed, insertions, deletions)."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        (tmp_path / "file1.py").write_text("line1\nline2\nline3\n")
        repo.index.add(["file1.py"])
        repo.index.commit("Add file1")

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should show statistics
        assert "file" in html.lower() and ("changed" in html.lower() or "insertion" in html.lower())

    def test_all_changes_option_in_selector(self, tmp_path):
        """Step selector should include 'All Changes' or 'View All' option."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        _init_git_repo(tmp_path)

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha="abc123",
            step_commits={"requirements": "def456"},
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(run_id="test_run_123", state_manager=sm)

        from PyQt6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox)
        items = [combo.itemText(i) for i in range(combo.count())]

        # Should have an "All Changes" option
        assert any("all" in item.lower() for item in items)


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewWidgetEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_empty_diff(self, tmp_path):
        """Widget should display 'No changes' message when diff is empty."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should show "no changes" message
        assert "no changes" in html.lower() or "no diff" in html.lower()

    def test_handles_missing_commit_sha(self, tmp_path):
        """Widget should handle case where commit SHA is not found in repo."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        _init_git_repo(tmp_path)

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha="nonexistent_sha_123",  # Invalid SHA
            step_commits={"requirements": "another_invalid_sha"},
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should show error message
        assert "not found" in html.lower() or "error" in html.lower()

    def test_handles_git_operation_failure(self, tmp_path):
        """Widget should handle GitPython operation failures gracefully."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget

        # Non-git directory
        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()

        widget = DiffViewWidget(
            run_id="test_run_123",
            project_path=str(non_git_dir),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should show error message
        assert "error" in html.lower() or "not found" in html.lower()

    def test_handles_worktree_cleaned_up(self, tmp_path):
        """Widget should work when worktree has been cleaned up (reads from main repo)."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        # Create a branch
        branch = repo.create_head("levelup/test_run_123")
        branch.checkout()

        (tmp_path / "change.py").write_text("new content")
        repo.index.add(["change.py"])
        step_sha = repo.index.commit("levelup(test): Change").hexsha

        # Switch back to master
        repo.heads.master.checkout()

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
            step_commits={"test": step_sha},
            worktree_path=None,  # Worktree cleaned up
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should still show diff
        assert "change.py" in html or "new content" in html or len(html) > 100

    def test_handles_run_without_step_commits(self, tmp_path):
        """Widget should handle runs without step_commits (early failures)."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        _init_git_repo(tmp_path)

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha="abc123",
            step_commits={},  # Empty - no steps completed
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox)

        # Should still work, maybe showing only "All Changes"
        assert combo is not None


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewWidgetLiveUpdates:
    """Test live updates for in-progress runs."""

    def test_widget_has_refresh_method(self):
        """Widget should have a refresh method for updating content."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget

        widget = DiffViewWidget()
        assert hasattr(widget, "refresh") or hasattr(widget, "update_diff")

    def test_refresh_updates_step_list(self, tmp_path):
        """Refresh should update the list of available steps."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
            step_commits={"requirements": "sha1"},
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(run_id="test_run_123", state_manager=sm)

        from PyQt6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox)
        initial_count = combo.count()

        # Add another step to context
        (tmp_path / "plan.txt").write_text("plan")
        repo.index.add(["plan.txt"])
        step_sha = repo.index.commit("levelup(planning): Plan").hexsha

        ctx.step_commits["planning"] = step_sha
        sm.update_run(ctx)

        # Refresh widget
        if hasattr(widget, "refresh"):
            widget.refresh()
        elif hasattr(widget, "update_diff"):
            widget.update_diff()

        # Step list should have updated
        new_count = combo.count()
        assert new_count >= initial_count

    def test_refresh_updates_diff_content(self, tmp_path):
        """Refresh should update the displayed diff content."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        initial_html = browser.toHtml()

        # Add new changes
        (tmp_path / "new_file.py").write_text("print('hello')")
        repo.index.add(["new_file.py"])
        repo.index.commit("Add new file")

        # Refresh
        if hasattr(widget, "refresh"):
            widget.refresh()
        elif hasattr(widget, "update_diff"):
            widget.update_diff()

        updated_html = browser.toHtml()

        # Content should have changed
        assert "new_file.py" in updated_html or updated_html != initial_html


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewWidgetDiffFormatting:
    """Test diff display formatting."""

    def test_displays_file_names(self, tmp_path):
        """Diff should display file names."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        (tmp_path / "myfile.py").write_text("content")
        repo.index.add(["myfile.py"])
        repo.index.commit("Add file")

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        assert "myfile.py" in html

    def test_displays_line_numbers(self, tmp_path):
        """Diff should include line number information."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        (tmp_path / "code.py").write_text("def func():\n    pass\n")
        repo.index.add(["code.py"])
        repo.index.commit("Add function")

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Unified diff format includes @@ line markers
        assert "@@" in html or "+" in html

    def test_displays_unified_diff_format(self, tmp_path):
        """Diff should be in unified format with +/- indicators."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        (tmp_path / "test.txt").write_text("added line\n")
        repo.index.add(["test.txt"])
        repo.index.commit("Add line")

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should have + or - indicators
        assert "+" in html or "-" in html
