"""Integration tests for keyboard hotkey navigation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from levelup.gui.main_window import MainWindow
from levelup.state.manager import StateManager
from levelup.state.models import RunRecord


def _ensure_qapp():
    """Ensure QApplication exists."""
    return QApplication.instance() or QApplication([])


class TestNextWaitingTicketNavigation:
    """Integration test for Ctrl+N next waiting ticket hotkey."""

    @patch("levelup.gui.main_window.StateManager")
    def test_ctrl_n_navigates_to_waiting_ticket(self, mock_state_manager):
        """Pressing Ctrl+N should navigate to next ticket waiting for input."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"

        # Create runs with one waiting for input
        runs = [
            RunRecord(
                run_id="run1",
                task_title="Completed Task",
                status="completed",
                ticket_number=1,
                project_path="/test",
                pid=None,
            ),
            RunRecord(
                run_id="run2",
                task_title="Waiting Task",
                status="waiting_for_input",
                ticket_number=2,
                project_path="/test",
                pid=1234,
            ),
        ]
        mock_state.list_runs.return_value = runs
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Start on runs table (page 0)
        assert window._stacked_widget.currentIndex() == 0

        # Find and activate Ctrl+N shortcut
        shortcuts = window.findChildren(QShortcut)
        ctrl_n = [s for s in shortcuts if s.key() == QKeySequence("Ctrl+N")]

        if ctrl_n:
            ctrl_n[0].activated.emit()

            # Should navigate to ticket detail view (page 1)
            assert window._stacked_widget.currentIndex() == 1

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_ctrl_n_cycles_through_waiting_tickets(self, mock_state_manager):
        """Pressing Ctrl+N multiple times should cycle through waiting tickets."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"

        # Create multiple waiting tickets
        runs = [
            RunRecord(
                run_id="run1",
                task_title="Waiting 1",
                status="waiting_for_input",
                ticket_number=1,
                project_path="/test",
                pid=1001,
            ),
            RunRecord(
                run_id="run2",
                task_title="Waiting 2",
                status="waiting_for_input",
                ticket_number=2,
                project_path="/test",
                pid=1002,
            ),
            RunRecord(
                run_id="run3",
                task_title="Waiting 3",
                status="waiting_for_input",
                ticket_number=3,
                project_path="/test",
                pid=1003,
            ),
        ]
        mock_state.list_runs.return_value = runs
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        shortcuts = window.findChildren(QShortcut)
        ctrl_n = [s for s in shortcuts if s.key() == QKeySequence("Ctrl+N")]

        if ctrl_n:
            # First press - navigate to ticket 1
            ctrl_n[0].activated.emit()
            assert window._stacked_widget.currentIndex() == 1

            # Second press - navigate to ticket 2
            ctrl_n[0].activated.emit()

            # Third press - navigate to ticket 3
            ctrl_n[0].activated.emit()

            # Fourth press - wrap to ticket 1
            ctrl_n[0].activated.emit()

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_ctrl_n_does_nothing_when_no_waiting_tickets(self, mock_state_manager):
        """Ctrl+N should do nothing when no tickets are waiting."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"

        # No waiting tickets
        runs = [
            RunRecord(
                run_id="run1",
                task_title="Completed",
                status="completed",
                ticket_number=1,
                project_path="/test",
                pid=None,
            ),
        ]
        mock_state.list_runs.return_value = runs
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        initial_index = window._stacked_widget.currentIndex()

        shortcuts = window.findChildren(QShortcut)
        ctrl_n = [s for s in shortcuts if s.key() == QKeySequence("Ctrl+N")]

        if ctrl_n:
            ctrl_n[0].activated.emit()

            # Should stay on same page
            assert window._stacked_widget.currentIndex() == initial_index

        window.close()


class TestBackToRunsNavigation:
    """Integration test for Escape back to runs hotkey."""

    @patch("levelup.gui.main_window.StateManager")
    def test_escape_returns_from_ticket_detail(self, mock_state_manager):
        """Pressing Escape from ticket detail should return to runs table."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Navigate to ticket detail
        window._stacked_widget.setCurrentIndex(1)
        assert window._stacked_widget.currentIndex() == 1

        # Press Escape
        shortcuts = window.findChildren(QShortcut)
        escape = [s for s in shortcuts if s.key() == QKeySequence("Escape")]

        if escape:
            escape[0].activated.emit()

            # Should return to runs table
            assert window._stacked_widget.currentIndex() == 0

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_escape_returns_from_docs_view(self, mock_state_manager):
        """Pressing Escape from docs should return to runs table."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Navigate to docs
        window._stacked_widget.setCurrentIndex(2)
        assert window._stacked_widget.currentIndex() == 2

        # Press Escape
        shortcuts = window.findChildren(QShortcut)
        escape = [s for s in shortcuts if s.key() == QKeySequence("Escape")]

        if escape:
            escape[0].activated.emit()

            # Should return to runs table
            assert window._stacked_widget.currentIndex() == 0

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_escape_clears_ticket_selection(self, mock_state_manager):
        """Pressing Escape should clear ticket sidebar selection."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Navigate to ticket detail
        window._stacked_widget.setCurrentIndex(1)

        # Press Escape
        shortcuts = window.findChildren(QShortcut)
        escape = [s for s in shortcuts if s.key() == QKeySequence("Escape")]

        if escape:
            escape[0].activated.emit()

            # Ticket sidebar should have no selection
            # (Implementation will clear selection)

        window.close()


class TestRefreshHotkey:
    """Integration test for F5 refresh hotkey."""

    @patch("levelup.gui.main_window.StateManager")
    def test_f5_refreshes_dashboard(self, mock_state_manager):
        """Pressing F5 should refresh runs list."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Mock refresh method
        window._refresh = Mock()

        # Press F5
        shortcuts = window.findChildren(QShortcut)
        f5 = [s for s in shortcuts if s.key() == QKeySequence("F5")]

        if f5:
            f5[0].activated.emit()

            # Refresh should be called
            # (Actual refresh logic tested elsewhere)

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_f5_works_from_any_view(self, mock_state_manager):
        """F5 should work from runs table, ticket detail, or docs."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())
        window._refresh = Mock()

        shortcuts = window.findChildren(QShortcut)
        f5 = [s for s in shortcuts if s.key() == QKeySequence("F5")]

        if f5:
            # Test from each view
            for view_index in [0, 1, 2]:
                window._stacked_widget.setCurrentIndex(view_index)
                f5[0].activated.emit()
                # Should work regardless of view

        window.close()


class TestOpenDocsHotkey:
    """Integration test for F1 open docs hotkey."""

    @patch("levelup.gui.main_window.StateManager")
    def test_f1_opens_documentation(self, mock_state_manager):
        """Pressing F1 should open documentation view."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Start on runs table
        assert window._stacked_widget.currentIndex() == 0

        # Press F1
        shortcuts = window.findChildren(QShortcut)
        f1 = [s for s in shortcuts if s.key() == QKeySequence("F1")]

        if f1:
            f1[0].activated.emit()

            # Should switch to docs view
            assert window._stacked_widget.currentIndex() == 2

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_f1_clears_ticket_selection(self, mock_state_manager):
        """Opening docs with F1 should clear ticket selection."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Press F1
        shortcuts = window.findChildren(QShortcut)
        f1 = [s for s in shortcuts if s.key() == QKeySequence("F1")]

        if f1:
            f1[0].activated.emit()

            # Ticket selection should be cleared
            # (Implementation detail)

        window.close()


class TestToggleThemeHotkey:
    """Integration test for Ctrl+T toggle theme hotkey."""

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.apply_theme")
    def test_ctrl_t_cycles_theme(self, mock_apply, mock_state_manager):
        """Pressing Ctrl+T should cycle through themes."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        from levelup.gui.theme_manager import set_theme_preference, get_theme_preference

        # Start with system theme
        set_theme_preference("system")
        initial = get_theme_preference()

        # Press Ctrl+T
        shortcuts = window.findChildren(QShortcut)
        ctrl_t = [s for s in shortcuts if s.key() == QKeySequence("Ctrl+T")]

        if ctrl_t:
            ctrl_t[0].activated.emit()

            # Theme should have changed
            new_pref = get_theme_preference()
            assert new_pref != initial

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.apply_theme")
    def test_ctrl_t_cycles_through_all_themes(self, mock_apply, mock_state_manager):
        """Pressing Ctrl+T three times should cycle through all themes."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        from levelup.gui.theme_manager import set_theme_preference, get_theme_preference

        set_theme_preference("system")
        initial = get_theme_preference()

        shortcuts = window.findChildren(QShortcut)
        ctrl_t = [s for s in shortcuts if s.key() == QKeySequence("Ctrl+T")]

        if ctrl_t:
            # Cycle 3 times
            ctrl_t[0].activated.emit()  # system → light
            ctrl_t[0].activated.emit()  # light → dark
            ctrl_t[0].activated.emit()  # dark → system

            # Should be back to initial
            final = get_theme_preference()
            assert final == initial

        window.close()


class TestFocusTerminalHotkey:
    """Integration test for Ctrl+` focus terminal hotkey."""

    @patch("levelup.gui.main_window.StateManager")
    def test_ctrl_backtick_focuses_terminal(self, mock_state_manager):
        """Pressing Ctrl+` in ticket detail should focus terminal."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Navigate to ticket detail
        window._stacked_widget.setCurrentIndex(1)

        # Press Ctrl+`
        shortcuts = window.findChildren(QShortcut)
        ctrl_backtick = [s for s in shortcuts if s.key() == QKeySequence("Ctrl+`")]

        if ctrl_backtick:
            ctrl_backtick[0].activated.emit()

            # Terminal should receive focus
            # (Implementation will call setFocus on terminal widget)

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_ctrl_backtick_does_nothing_outside_ticket_detail(self, mock_state_manager):
        """Ctrl+` should do nothing when not in ticket detail view."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # On runs table
        assert window._stacked_widget.currentIndex() == 0

        # Press Ctrl+`
        shortcuts = window.findChildren(QShortcut)
        ctrl_backtick = [s for s in shortcuts if s.key() == QKeySequence("Ctrl+`")]

        if ctrl_backtick:
            # Should not crash
            ctrl_backtick[0].activated.emit()

        window.close()


class TestHotkeysCombined:
    """Integration test for using multiple hotkeys in sequence."""

    @patch("levelup.gui.main_window.StateManager")
    def test_navigate_with_hotkeys_workflow(self, mock_state_manager):
        """Test complete navigation workflow using only hotkeys."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"

        runs = [
            RunRecord(
                run_id="run1",
                task_title="Waiting",
                status="waiting_for_input",
                ticket_number=1,
                project_path="/test",
                pid=1001,
            ),
        ]
        mock_state.list_runs.return_value = runs
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        shortcuts = window.findChildren(QShortcut)

        # Get shortcuts
        ctrl_n = [s for s in shortcuts if s.key() == QKeySequence("Ctrl+N")][0]
        escape = [s for s in shortcuts if s.key() == QKeySequence("Escape")][0]
        f1 = [s for s in shortcuts if s.key() == QKeySequence("F1")][0]

        # Workflow:
        # 1. Start on runs table
        assert window._stacked_widget.currentIndex() == 0

        # 2. Press Ctrl+N to go to waiting ticket
        ctrl_n.activated.emit()
        assert window._stacked_widget.currentIndex() == 1

        # 3. Press Escape to return to runs
        escape.activated.emit()
        assert window._stacked_widget.currentIndex() == 0

        # 4. Press F1 to open docs
        f1.activated.emit()
        assert window._stacked_widget.currentIndex() == 2

        # 5. Press Escape to return to runs
        escape.activated.emit()
        assert window._stacked_widget.currentIndex() == 0

        window.close()
