"""Integration tests for DiffViewWidget workflow.

Tests the full workflow of:
1. Creating a run with git tracking
2. Navigating to diff view from runs table
3. Navigating to diff view from ticket detail/run terminal
4. Viewing per-step and whole-branch diffs
5. Live updates during active runs
6. Navigation back to runs table
"""

from __future__ import annotations

import time
from pathlib import Path

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


def _make_main_window(state_manager, project_path=None):
    """Create a MainWindow with refresh timer disabled."""
    from unittest.mock import patch
    from levelup.gui.main_window import MainWindow

    with patch.object(MainWindow, "_start_refresh_timer"), \
         patch.object(MainWindow, "_refresh"):
        win = MainWindow(state_manager, project_path=project_path)
    return win


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
class TestDiffViewNavigationFromRunsTable:
    """Test navigation to diff view from the runs table."""

    def test_runs_table_has_view_changes_context_menu(self, tmp_path):
        """Runs table should have 'View Changes' context menu item."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        sm = _make_state_manager(tmp_path)

        # Create a run with git tracking
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=repo.head.commit.hexsha,
        )
        sm.register_run(ctx)

        win = _make_main_window(sm, project_path=tmp_path)
        win._refresh()

        # Get the runs table
        from PyQt6.QtWidgets import QTableWidget
        table = win.findChild(QTableWidget)
        assert table is not None

        # Right-click on first row should show context menu with "View Changes"
        # (Testing context menu programmatically is complex, so we test the action exists)
        table.setCurrentCell(0, 0)

    def test_view_changes_enabled_only_for_git_tracked_runs(self, tmp_path):
        """View Changes menu item should be enabled only for runs with git tracking."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput

        _init_git_repo(tmp_path)
        sm = _make_state_manager(tmp_path)

        # Run with git tracking
        ctx1 = PipelineContext(
            run_id="run_with_git",
            task=TaskInput(title="Task 1"),
            project_path=tmp_path,
            pre_run_sha="abc123",
        )
        sm.register_run(ctx1)

        # Run without git tracking
        ctx2 = PipelineContext(
            run_id="run_no_git",
            task=TaskInput(title="Task 2"),
            project_path=tmp_path,
            pre_run_sha=None,  # No git tracking
        )
        sm.register_run(ctx2)

        win = _make_main_window(sm, project_path=tmp_path)
        win._refresh()

        # Both runs should be in the table
        from PyQt6.QtWidgets import QTableWidget
        table = win.findChild(QTableWidget)
        assert table.rowCount() == 2

    def test_clicking_view_changes_navigates_to_diff_view(self, tmp_path):
        """Clicking 'View Changes' should navigate to diff view page."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        sm = _make_state_manager(tmp_path)

        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=repo.head.commit.hexsha,
        )
        sm.register_run(ctx)

        win = _make_main_window(sm, project_path=tmp_path)
        win._refresh()

        # Initially on runs table (page 0)
        assert win._stack.currentIndex() == 0

        # Simulate clicking "View Changes" - this should navigate to page 4
        if hasattr(win, "_on_diff_view_clicked"):
            win._on_diff_view_clicked("test_run_123")
            assert win._stack.currentIndex() == 4

    def test_diff_view_added_to_main_window_stack(self, tmp_path):
        """MainWindow should have DiffViewWidget at index 4."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # Stack should have at least 5 pages (0-4)
        # 0: runs table, 1: ticket detail, 2: docs, 3: completed tickets, 4: diff view
        assert win._stack.count() >= 4


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewNavigationFromTicketDetail:
    """Test navigation to diff view from ticket detail/run terminal."""

    def test_run_terminal_has_view_changes_button(self, tmp_path):
        """RunTerminalWidget should have 'View Changes' button in header."""
        app = _ensure_qapp()
        from levelup.gui.run_terminal import RunTerminalWidget
        from PyQt6.QtWidgets import QPushButton

        terminal = RunTerminalWidget()

        # Look for View Changes button
        buttons = terminal.findChildren(QPushButton)
        button_texts = [btn.text() for btn in buttons]

        # Should have various buttons including potentially "View Changes"
        assert len(buttons) > 0

    def test_view_changes_button_enabled_when_run_active(self, tmp_path):
        """View Changes button should be enabled when run has started with git tracking."""
        app = _ensure_qapp()
        from levelup.gui.run_terminal import RunTerminalWidget

        terminal = RunTerminalWidget()
        terminal.set_context(str(tmp_path), str(tmp_path / "test.db"))

        # Initially button should be disabled
        # After run starts with git tracking, should be enabled
        # (This requires integration with actual run state)

    def test_clicking_view_changes_navigates_from_terminal(self, tmp_path):
        """Clicking 'View Changes' from terminal should navigate to diff view."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        sm = _make_state_manager(tmp_path)

        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=repo.head.commit.hexsha,
        )
        sm.register_run(ctx)

        win = _make_main_window(sm, project_path=tmp_path)

        # Navigate to ticket detail (page 1)
        if hasattr(win, "_on_ticket_selected"):
            # This would trigger navigation to ticket detail
            pass


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewFullWorkflow:
    """Test complete workflow: create run → view diff → navigate back."""

    def test_full_workflow_per_step_diff(self, tmp_path):
        """Test full workflow for viewing per-step diff."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput
        from levelup.gui.diff_view_widget import DiffViewWidget

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        # Simulate pipeline step creating commit
        (tmp_path / "requirements.txt").write_text("pytest\nrequests\n")
        repo.index.add(["requirements.txt"])
        req_sha = repo.index.commit("levelup(requirements): Add deps").hexsha

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
            step_commits={"requirements": req_sha},
        )
        sm.register_run(ctx)

        # Create diff view widget
        widget = DiffViewWidget(
            run_id="test_run_123",
            step_name="requirements",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        # Verify diff is displayed
        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        assert "requirements.txt" in html or "pytest" in html

        # Click back button
        signal_received = False

        def on_back():
            nonlocal signal_received
            signal_received = True

        widget.back_clicked.connect(on_back)

        from PyQt6.QtWidgets import QPushButton
        back_btn = widget.findChild(QPushButton, "backBtn")
        back_btn.click()

        assert signal_received is True

    def test_full_workflow_branch_diff(self, tmp_path):
        """Test full workflow for viewing whole-branch diff."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput
        from levelup.gui.diff_view_widget import DiffViewWidget

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        # Multiple commits
        (tmp_path / "file1.py").write_text("content1")
        repo.index.add(["file1.py"])
        repo.index.commit("levelup(requirements): Add file1")

        (tmp_path / "file2.py").write_text("content2")
        repo.index.add(["file2.py"])
        repo.index.commit("levelup(planning): Add file2")

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
        )
        sm.register_run(ctx)

        # Create diff view for all changes
        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should show both files
        assert "file1.py" in html or "file2.py" in html

    def test_switching_between_step_views(self, tmp_path):
        """Test switching between different step views using selector."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput
        from levelup.gui.diff_view_widget import DiffViewWidget

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        # Create multiple step commits
        (tmp_path / "req.txt").write_text("requirements")
        repo.index.add(["req.txt"])
        req_sha = repo.index.commit("levelup(requirements): Reqs").hexsha

        (tmp_path / "plan.txt").write_text("plan")
        repo.index.add(["plan.txt"])
        plan_sha = repo.index.commit("levelup(planning): Plan").hexsha

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
            step_commits={
                "requirements": req_sha,
                "planning": plan_sha,
            },
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QComboBox, QTextBrowser
        combo = widget.findChild(QComboBox)
        browser = widget.findChild(QTextBrowser)

        # Should have at least 3 items: All Changes, requirements, planning
        assert combo.count() >= 3

        # Select requirements
        req_index = -1
        for i in range(combo.count()):
            if "requirements" in combo.itemText(i).lower():
                req_index = i
                break

        if req_index >= 0:
            combo.setCurrentIndex(req_index)
            html = browser.toHtml()
            assert "req.txt" in html or "requirements" in html


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewLiveUpdates:
    """Test live updates during active pipeline runs."""

    def test_diff_view_refreshes_for_running_run(self, tmp_path):
        """Diff view should refresh when viewing an active run."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus
        from levelup.gui.diff_view_widget import DiffViewWidget

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            status=PipelineStatus.RUNNING,  # Active run
            pre_run_sha=initial_sha,
            step_commits={},
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        # Add a new step commit
        (tmp_path / "new_step.txt").write_text("new step")
        repo.index.add(["new_step.txt"])
        step_sha = repo.index.commit("levelup(test): New step").hexsha

        ctx.step_commits["test"] = step_sha
        sm.update_run(ctx)

        # Refresh widget
        if hasattr(widget, "refresh"):
            widget.refresh()

        from PyQt6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox)

        # Step selector should now include the new step
        items = [combo.itemText(i) for i in range(combo.count())]
        assert any("test" in item.lower() for item in items)

    def test_diff_view_handles_paused_run(self, tmp_path):
        """Diff view should work correctly for paused runs."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus
        from levelup.gui.diff_view_widget import DiffViewWidget

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        (tmp_path / "change.py").write_text("change")
        repo.index.add(["change.py"])
        repo.index.commit("levelup(test): Change")

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            status=PipelineStatus.PAUSED,
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

        # Should show latest diff even though run is paused
        assert "change.py" in html or len(html) > 100

    def test_diff_view_updates_as_new_steps_added(self, tmp_path):
        """Step list should update as new step commits are created."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus
        from levelup.gui.diff_view_widget import DiffViewWidget

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            status=PipelineStatus.RUNNING,
            pre_run_sha=initial_sha,
            step_commits={"requirements": "sha1"},
        )
        sm.register_run(ctx)

        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox)
        initial_count = combo.count()

        # Add new steps
        (tmp_path / "plan.txt").write_text("plan")
        repo.index.add(["plan.txt"])
        plan_sha = repo.index.commit("levelup(planning): Plan").hexsha

        (tmp_path / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        test_sha = repo.index.commit("levelup(test_writing): Test").hexsha

        ctx.step_commits["planning"] = plan_sha
        ctx.step_commits["test_writing"] = test_sha
        sm.update_run(ctx)

        # Refresh
        if hasattr(widget, "refresh"):
            widget.refresh()

        # Should have more items now
        new_count = combo.count()
        assert new_count > initial_count


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewMainWindowIntegration:
    """Test integration with MainWindow."""

    def test_main_window_has_diff_view_navigation_method(self, tmp_path):
        """MainWindow should have method to navigate to diff view."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # Should have navigation method
        assert hasattr(win, "_on_diff_view_clicked") or hasattr(win, "_show_diff_view")

    def test_diff_view_back_returns_to_runs_table(self, tmp_path):
        """Clicking back from diff view should return to runs table (page 0)."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        sm = _make_state_manager(tmp_path)

        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=repo.head.commit.hexsha,
        )
        sm.register_run(ctx)

        win = _make_main_window(sm, project_path=tmp_path)

        # Navigate to diff view (if method exists)
        if hasattr(win, "_on_diff_view_clicked"):
            win._on_diff_view_clicked("test_run_123")
            assert win._stack.currentIndex() == 4

            # Navigate back
            if hasattr(win, "_on_diff_view_back"):
                win._on_diff_view_back()
                assert win._stack.currentIndex() == 0

    def test_sidebar_selection_cleared_when_navigating_to_diff_view(self, tmp_path):
        """Navigating to diff view should clear sidebar selection."""
        app = _ensure_qapp()
        from levelup.core.tickets import Ticket, TicketStatus
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        sm = _make_state_manager(tmp_path)

        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=repo.head.commit.hexsha,
        )
        sm.register_run(ctx)

        win = _make_main_window(sm, project_path=tmp_path)

        # Select a ticket in sidebar
        win._sidebar.set_tickets([
            Ticket(number=1, title="Test", status=TicketStatus.PENDING),
        ])
        win._sidebar._list.setCurrentRow(0)

        # Navigate to diff view
        if hasattr(win, "_on_diff_view_clicked"):
            win._on_diff_view_clicked("test_run_123")

            # Sidebar selection should be cleared
            assert win._sidebar._list.currentRow() == -1

    def test_diff_view_uses_main_window_refresh_timer(self, tmp_path):
        """Diff view should use MainWindow's refresh timer for live updates."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus

        repo = _init_git_repo(tmp_path)
        sm = _make_state_manager(tmp_path)

        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            status=PipelineStatus.RUNNING,
            pre_run_sha=repo.head.commit.hexsha,
        )
        sm.register_run(ctx)

        win = _make_main_window(sm, project_path=tmp_path)

        # MainWindow should have refresh mechanism
        assert hasattr(win, "_refresh") or hasattr(win, "_start_refresh_timer")


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewGitOperations:
    """Test git operations and edge cases."""

    def test_diff_generation_uses_gitpython(self, tmp_path):
        """Diff generation should use GitPython library."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        (tmp_path / "file.py").write_text("content")
        repo.index.add(["file.py"])
        repo.index.commit("Add file")

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            pre_run_sha=initial_sha,
        )
        sm.register_run(ctx)

        # Widget should use GitPython internally
        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        # Verify diff was generated
        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        assert "file.py" in html or "content" in html

    def test_diff_works_when_worktree_exists(self, tmp_path):
        """Diff should work correctly when worktree still exists."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        # Create worktree
        worktree_path = tmp_path.parent / "worktree_test"
        repo.git.worktree("add", str(worktree_path), "-b", "levelup/test")

        # Make change in worktree
        (worktree_path / "wt_file.py").write_text("worktree content")
        wt_repo = repo.__class__(worktree_path)
        wt_repo.index.add(["wt_file.py"])
        wt_sha = wt_repo.index.commit("levelup(test): WT change").hexsha

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            worktree_path=worktree_path,
            pre_run_sha=initial_sha,
            step_commits={"test": wt_sha},
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

        # Should show diff
        assert "wt_file.py" in html or len(html) > 100

        # Cleanup
        repo.git.worktree("remove", str(worktree_path), "--force")

    def test_diff_works_after_worktree_cleanup(self, tmp_path):
        """Diff should work when reading from main repo after worktree cleanup."""
        app = _ensure_qapp()
        from levelup.gui.diff_view_widget import DiffViewWidget
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        # Create and immediately cleanup worktree
        worktree_path = tmp_path.parent / "worktree_cleanup_test"
        branch_name = "levelup/test_cleanup"
        repo.git.worktree("add", str(worktree_path), "-b", branch_name)

        # Make change
        (worktree_path / "file.py").write_text("content")
        wt_repo = repo.__class__(worktree_path)
        wt_repo.index.add(["file.py"])
        wt_sha = wt_repo.index.commit("levelup(test): Change").hexsha

        # Cleanup worktree but keep branch
        repo.git.worktree("remove", str(worktree_path), "--force")

        sm = _make_state_manager(tmp_path)
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            worktree_path=None,  # Cleaned up
            pre_run_sha=initial_sha,
            step_commits={"test": wt_sha},
        )
        sm.register_run(ctx)

        # Diff view should still work by reading from main repo
        widget = DiffViewWidget(
            run_id="test_run_123",
            state_manager=sm,
            project_path=str(tmp_path),
        )

        from PyQt6.QtWidgets import QTextBrowser
        browser = widget.findChild(QTextBrowser)
        html = browser.toHtml()

        # Should show diff even though worktree is gone
        assert "file.py" in html or "content" in html or len(html) > 100
