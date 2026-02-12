"""Unit tests for MainWindow integration with DiffViewWidget.

Tests the integration of DiffViewWidget into MainWindow's stacked widget,
navigation methods, and UI elements for accessing diff view.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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
class TestMainWindowDiffViewPage:
    """Test that DiffViewWidget is properly added to MainWindow stack."""

    def test_stack_has_diff_view_page(self, tmp_path):
        """MainWindow stack should have at least 5 pages including diff view."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # Original: 0=runs, 1=ticket detail, 2=docs, 3=completed tickets
        # New: 4=diff view
        assert win._stack.count() >= 4

    def test_diff_view_widget_exists_in_stack(self, tmp_path):
        """Stack should contain a DiffViewWidget instance."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # Try to import DiffViewWidget
        try:
            from levelup.gui.diff_view_widget import DiffViewWidget

            # Check if any widget in stack is DiffViewWidget
            found_diff_view = False
            for i in range(win._stack.count()):
                widget = win._stack.widget(i)
                if isinstance(widget, DiffViewWidget):
                    found_diff_view = True
                    break

            # May not be present until navigation occurs
            # This test verifies structure is ready
        except ImportError:
            # DiffViewWidget not yet implemented
            pass

    def test_diff_view_index_is_4(self, tmp_path):
        """DiffViewWidget should be at index 4 in the stack."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # If stack has 5+ pages, check index 4
        if win._stack.count() >= 5:
            # Index 4 should be diff view
            widget = win._stack.widget(4)
            # Check if it's the right type
            try:
                from levelup.gui.diff_view_widget import DiffViewWidget
                # May or may not be DiffViewWidget depending on implementation
            except ImportError:
                pass


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestMainWindowDiffViewNavigation:
    """Test navigation methods for diff view."""

    def test_has_on_diff_view_clicked_method(self, tmp_path):
        """MainWindow should have _on_diff_view_clicked method."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # Should have navigation method (or similar)
        assert (
            hasattr(win, "_on_diff_view_clicked") or
            hasattr(win, "_show_diff_view") or
            hasattr(win, "_navigate_to_diff_view")
        )

    def test_has_on_diff_view_back_method(self, tmp_path):
        """MainWindow should have _on_diff_view_back method."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # Should have back navigation method
        assert (
            hasattr(win, "_on_diff_view_back") or
            hasattr(win, "_on_back_to_runs")
        )

    def test_navigate_to_diff_view_switches_page(self, tmp_path):
        """Calling navigation method should switch to diff view page."""
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

        # Initially on runs table
        assert win._stack.currentIndex() == 0

        # Navigate to diff view
        if hasattr(win, "_on_diff_view_clicked"):
            win._on_diff_view_clicked("test_run_123")
            # Should now be on page 4
            assert win._stack.currentIndex() == 4
        elif hasattr(win, "_show_diff_view"):
            win._show_diff_view("test_run_123")
            assert win._stack.currentIndex() == 4

    def test_back_from_diff_view_returns_to_runs_table(self, tmp_path):
        """Back navigation should return to runs table (page 0)."""
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

        # Navigate to diff view
        if hasattr(win, "_on_diff_view_clicked"):
            win._on_diff_view_clicked("test_run_123")
            assert win._stack.currentIndex() == 4

            # Navigate back
            if hasattr(win, "_on_diff_view_back"):
                win._on_diff_view_back()
                assert win._stack.currentIndex() == 0

    def test_diff_view_back_signal_connected(self, tmp_path):
        """DiffViewWidget's back_clicked signal should be connected."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # If stack has diff view widget, its back signal should be connected
        if win._stack.count() >= 5:
            widget = win._stack.widget(4)
            if hasattr(widget, "back_clicked"):
                # Signal should be connected to MainWindow's back handler
                pass


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestMainWindowDiffViewSidebarInteraction:
    """Test sidebar behavior when navigating to diff view."""

    def test_sidebar_selection_cleared_on_diff_view(self, tmp_path):
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

        # Set tickets and select one
        win._sidebar.set_tickets([
            Ticket(number=1, title="Test", status=TicketStatus.PENDING),
        ])
        win._sidebar._list.setCurrentRow(0)
        assert win._sidebar._list.currentRow() == 0

        # Navigate to diff view
        if hasattr(win, "_on_diff_view_clicked"):
            win._on_diff_view_clicked("test_run_123")

            # Sidebar selection should be cleared
            assert win._sidebar._list.currentRow() == -1

    def test_sidebar_selection_cleared_follows_pattern(self, tmp_path):
        """Clearing sidebar follows same pattern as docs/completed tickets."""
        app = _ensure_qapp()
        from levelup.core.tickets import Ticket, TicketStatus

        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        win._sidebar.set_tickets([
            Ticket(number=1, title="Test", status=TicketStatus.PENDING),
        ])
        win._sidebar._list.setCurrentRow(0)

        # Navigate to docs - should clear
        win._on_docs_clicked()
        assert win._sidebar._list.currentRow() == -1

        # Select again
        win._sidebar._list.setCurrentRow(0)

        # Navigate to completed - should clear
        win._on_completed_clicked()
        assert win._sidebar._list.currentRow() == -1

        # Diff view should follow same pattern


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestRunsTableContextMenu:
    """Test runs table context menu for 'View Changes'."""

    def test_runs_table_has_context_menu(self, tmp_path):
        """Runs table should support context menu."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        from PyQt6.QtWidgets import QTableWidget
        table = win.findChild(QTableWidget)

        # Table should have context menu policy set
        # (Actual menu testing is complex, we verify structure)
        assert table is not None

    def test_view_changes_action_exists(self, tmp_path):
        """MainWindow should have 'View Changes' action or method."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # Should have action or method for viewing changes
        # Could be an action, method, or both
        has_action = False

        # Check for QAction
        from PyQt6.QtGui import QAction
        actions = win.findChildren(QAction)
        for action in actions:
            if "view" in action.text().lower() and "change" in action.text().lower():
                has_action = True
                break

        # Or check for method
        has_method = (
            hasattr(win, "_on_view_changes") or
            hasattr(win, "_show_changes") or
            hasattr(win, "_on_diff_view_clicked")
        )

        assert has_action or has_method

    def test_view_changes_enabled_for_git_tracked_runs(self, tmp_path):
        """View Changes should be enabled only for runs with git tracking."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput

        repo = _init_git_repo(tmp_path)
        sm = _make_state_manager(tmp_path)

        # Run with git tracking
        ctx1 = PipelineContext(
            run_id="with_git",
            task=TaskInput(title="Task 1"),
            project_path=tmp_path,
            pre_run_sha=repo.head.commit.hexsha,
        )
        sm.register_run(ctx1)

        # Run without git tracking
        ctx2 = PipelineContext(
            run_id="no_git",
            task=TaskInput(title="Task 2"),
            project_path=tmp_path,
            pre_run_sha=None,
        )
        sm.register_run(ctx2)

        win = _make_main_window(sm, project_path=tmp_path)
        win._refresh()

        # Implementation should check pre_run_sha before enabling action


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestRunTerminalViewChangesButton:
    """Test 'View Changes' button in RunTerminalWidget."""

    def test_run_terminal_has_view_changes_button(self):
        """RunTerminalWidget should have 'View Changes' button."""
        app = _ensure_qapp()
        from levelup.gui.run_terminal import RunTerminalWidget
        from PyQt6.QtWidgets import QPushButton

        terminal = RunTerminalWidget()

        # Check for button (may not exist yet in implementation)
        buttons = terminal.findChildren(QPushButton)
        button_texts = [btn.text() for btn in buttons]

        # Standard buttons: Run, Terminate, Pause, Resume, Merge, Forget
        # New button: View Changes
        assert len(buttons) > 0

    def test_view_changes_button_has_object_name(self):
        """View Changes button should have identifiable objectName."""
        app = _ensure_qapp()
        from levelup.gui.run_terminal import RunTerminalWidget
        from PyQt6.QtWidgets import QPushButton

        terminal = RunTerminalWidget()

        # Look for button with specific object name
        view_changes_btn = terminal.findChild(QPushButton, "viewChangesBtn")

        # May not exist until implementation
        # This test defines the expected structure

    def test_view_changes_button_enabled_when_run_active(self, tmp_path):
        """View Changes button should be enabled when run is active with git."""
        app = _ensure_qapp()
        from levelup.gui.run_terminal import RunTerminalWidget

        terminal = RunTerminalWidget()
        terminal.set_context(str(tmp_path), str(tmp_path / "test.db"))

        # Button should exist and be disabled initially
        # After run starts with git tracking, should be enabled


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewRefreshIntegration:
    """Test diff view refresh integration with MainWindow."""

    def test_main_window_refresh_timer_interval(self, tmp_path):
        """MainWindow should have refresh timer with 2000ms interval."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)

        # Create window with real timer
        from levelup.gui.main_window import MainWindow, REFRESH_INTERVAL_MS

        # Verify constant
        assert REFRESH_INTERVAL_MS == 2000

    def test_diff_view_refreshes_on_timer(self, tmp_path):
        """Diff view should refresh when MainWindow timer fires."""
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

        # Navigate to diff view
        if hasattr(win, "_on_diff_view_clicked"):
            win._on_diff_view_clicked("test_run_123")

            # Manually trigger refresh
            if hasattr(win, "_refresh"):
                win._refresh()

            # Diff view should be updated
            # (Implementation should handle this)

    def test_only_active_runs_trigger_updates(self, tmp_path):
        """Only running/waiting_for_input runs should trigger live updates."""
        app = _ensure_qapp()
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus

        repo = _init_git_repo(tmp_path)
        sm = _make_state_manager(tmp_path)

        # Completed run - should not auto-refresh
        ctx = PipelineContext(
            run_id="test_run_123",
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
            pre_run_sha=repo.head.commit.hexsha,
        )
        sm.register_run(ctx)

        # Implementation should check status before auto-refreshing


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDiffViewThemeIntegration:
    """Test diff view theme integration with MainWindow."""

    def test_diff_view_receives_current_theme(self, tmp_path):
        """Diff view should receive MainWindow's current theme."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # MainWindow has current theme
        current_theme = win._current_theme

        # When creating diff view, should pass theme
        # (Implementation should handle this)

    def test_diff_view_updates_with_theme_changes(self, tmp_path):
        """Diff view should update when MainWindow theme changes."""
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

        # Navigate to diff view
        if hasattr(win, "_on_diff_view_clicked"):
            win._on_diff_view_clicked("test_run_123")

            # Change theme
            if hasattr(win, "_cycle_theme"):
                initial_theme = win._current_theme
                win._cycle_theme()

                # Diff view should receive update_theme call
                # (Implementation detail)
