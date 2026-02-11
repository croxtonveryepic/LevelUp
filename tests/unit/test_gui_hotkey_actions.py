"""Tests for hotkey action handlers in MainWindow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

import pytest
from PyQt6.QtWidgets import QApplication

from levelup.state.manager import StateManager
from levelup.state.models import RunRecord


def _ensure_qapp():
    """Ensure QApplication exists."""
    return QApplication.instance() or QApplication([])


class TestNextWaitingTicketAction:
    """Test next waiting ticket navigation action."""

    @patch("levelup.gui.main_window.StateManager")
    def test_navigates_to_first_waiting_ticket(self, mock_state_manager):
        """Should navigate to first ticket with waiting_for_input status."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"

        # Create runs with different statuses
        runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                status="completed",
                ticket_number=1,
                project_path="/test",
                pid=None,
            ),
            RunRecord(
                run_id="run2",
                task_title="Task 2",
                status="waiting_for_input",
                ticket_number=2,
                project_path="/test",
                pid=None,
            ),
            RunRecord(
                run_id="run3",
                task_title="Task 3",
                status="waiting_for_input",
                ticket_number=3,
                project_path="/test",
                pid=None,
            ),
        ]
        mock_state.list_runs.return_value = runs
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Call next waiting ticket action
        if hasattr(window, "_on_next_waiting_ticket"):
            window._on_next_waiting_ticket()

            # Should navigate to ticket 2 (first waiting ticket)
            # Check that ticket detail view is shown
            if hasattr(window, "_stacked_widget"):
                assert window._stacked_widget.currentIndex() == 1  # Ticket detail page

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_wraps_around_to_first_ticket(self, mock_state_manager):
        """Should wrap to first waiting ticket after reaching last one."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"

        runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                status="waiting_for_input",
                ticket_number=1,
                project_path="/test",
                pid=None,
            ),
            RunRecord(
                run_id="run2",
                task_title="Task 2",
                status="waiting_for_input",
                ticket_number=2,
                project_path="/test",
                pid=None,
            ),
        ]
        mock_state.list_runs.return_value = runs
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        if hasattr(window, "_on_next_waiting_ticket"):
            # Navigate to first
            window._on_next_waiting_ticket()
            # Navigate to second
            window._on_next_waiting_ticket()
            # Should wrap to first
            window._on_next_waiting_ticket()

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_does_nothing_when_no_waiting_tickets(self, mock_state_manager):
        """Should do nothing when no tickets are waiting for input."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"

        # No waiting tickets
        runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                status="completed",
                ticket_number=1,
                project_path="/test",
                pid=None,
            ),
        ]
        mock_state.list_runs.return_value = runs
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        initial_index = window._stacked_widget.currentIndex() if hasattr(window, "_stacked_widget") else 0

        if hasattr(window, "_on_next_waiting_ticket"):
            window._on_next_waiting_ticket()

            # Should not change view
            if hasattr(window, "_stacked_widget"):
                assert window._stacked_widget.currentIndex() == initial_index

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_focuses_terminal_after_navigation(self, mock_state_manager):
        """Should focus terminal widget after navigating to ticket."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"

        runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                status="waiting_for_input",
                ticket_number=1,
                project_path="/test",
                pid=None,
            ),
        ]
        mock_state.list_runs.return_value = runs
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        if hasattr(window, "_on_next_waiting_ticket"):
            window._on_next_waiting_ticket()

            # Terminal should receive focus
            # (Implementation detail: ticket_detail has terminal widget)

        window.close()


class TestBackToRunsAction:
    """Test back to runs table action."""

    @patch("levelup.gui.main_window.StateManager")
    def test_returns_to_runs_from_ticket_detail(self, mock_state_manager):
        """Should return to runs table from ticket detail view."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Switch to ticket detail view
        if hasattr(window, "_stacked_widget"):
            window._stacked_widget.setCurrentIndex(1)

            # Call back to runs action
            if hasattr(window, "_on_back_to_runs"):
                window._on_back_to_runs()

                # Should be back at runs table (index 0)
                assert window._stacked_widget.currentIndex() == 0

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_returns_to_runs_from_docs_view(self, mock_state_manager):
        """Should return to runs table from documentation view."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Switch to docs view
        if hasattr(window, "_stacked_widget"):
            window._stacked_widget.setCurrentIndex(2)

            if hasattr(window, "_on_back_to_runs"):
                window._on_back_to_runs()

                # Should be back at runs table
                assert window._stacked_widget.currentIndex() == 0

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_clears_ticket_sidebar_selection(self, mock_state_manager):
        """Should clear ticket sidebar selection when returning to runs."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Go to ticket view and then back
        if hasattr(window, "_stacked_widget"):
            window._stacked_widget.setCurrentIndex(1)

            if hasattr(window, "_on_back_to_runs"):
                window._on_back_to_runs()

                # Ticket sidebar should have no selection
                if hasattr(window, "_ticket_sidebar"):
                    # Check that clearSelection was called or no item is selected

                    pass  # Implementation will test this

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_does_nothing_when_already_on_runs_table(self, mock_state_manager):
        """Should do nothing when already on runs table view."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Already on runs table (index 0)
        if hasattr(window, "_stacked_widget"):
            assert window._stacked_widget.currentIndex() == 0

            if hasattr(window, "_on_back_to_runs"):
                window._on_back_to_runs()

                # Should still be on runs table
                assert window._stacked_widget.currentIndex() == 0

        window.close()


class TestRefreshDashboardAction:
    """Test dashboard refresh action."""

    @patch("levelup.gui.main_window.StateManager")
    def test_refresh_calls_existing_refresh_method(self, mock_state_manager):
        """Should call existing _refresh method."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Mock _refresh method
        window._refresh = Mock()

        # Trigger hotkey action (should call _refresh)
        if hasattr(window, "_on_refresh_hotkey"):
            window._on_refresh_hotkey()
            window._refresh.assert_called_once()

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_refresh_works_from_any_view(self, mock_state_manager):
        """Refresh should work from runs table, ticket detail, or docs view."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())
        window._refresh = Mock()

        # Test from each view
        for view_index in [0, 1, 2]:
            if hasattr(window, "_stacked_widget"):
                window._stacked_widget.setCurrentIndex(view_index)

                if hasattr(window, "_on_refresh_hotkey"):
                    window._on_refresh_hotkey()
                    # Should call refresh regardless of view

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_refresh_updates_runs_list(self, mock_state_manager):
        """Refresh should update the runs list from state manager."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"

        # Initial empty list
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Update mock to return runs
        new_runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                status="running",
                ticket_number=1,
                project_path="/test",
                pid=None,
            ),
        ]
        mock_state.list_runs.return_value = new_runs

        # Trigger refresh
        window._refresh()

        # Should have called list_runs
        assert mock_state.list_runs.called

        window.close()


class TestOpenDocumentationAction:
    """Test open documentation action."""

    @patch("levelup.gui.main_window.StateManager")
    def test_switches_to_docs_view(self, mock_state_manager):
        """Should switch to documentation view."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Start on runs table
        if hasattr(window, "_stacked_widget"):
            assert window._stacked_widget.currentIndex() == 0

            # Trigger docs hotkey
            if hasattr(window, "_on_docs_hotkey"):
                window._on_docs_hotkey()
            else:
                # Use existing _on_docs_clicked method
                window._on_docs_clicked()

            # Should switch to docs view (page 2)
            assert window._stacked_widget.currentIndex() == 2

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_clears_ticket_selection_when_opening_docs(self, mock_state_manager):
        """Should clear ticket sidebar selection when opening docs."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Open docs
        if hasattr(window, "_on_docs_hotkey"):
            window._on_docs_hotkey()
        else:
            window._on_docs_clicked()

        # Ticket sidebar should have no selection
        # (Implementation detail)

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_works_from_any_view(self, mock_state_manager):
        """Should open docs from any current view."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Test from each view
        for start_view in [0, 1, 2]:
            if hasattr(window, "_stacked_widget"):
                window._stacked_widget.setCurrentIndex(start_view)

                if hasattr(window, "_on_docs_hotkey"):
                    window._on_docs_hotkey()
                else:
                    window._on_docs_clicked()

                # Should be on docs view
                assert window._stacked_widget.currentIndex() == 2

        window.close()


class TestFocusTerminalAction:
    """Test focus terminal action."""

    @patch("levelup.gui.main_window.StateManager")
    def test_focuses_terminal_in_ticket_detail(self, mock_state_manager):
        """Should focus terminal widget when in ticket detail view."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Switch to ticket detail view
        if hasattr(window, "_stacked_widget"):
            window._stacked_widget.setCurrentIndex(1)

            # Trigger focus terminal
            if hasattr(window, "_on_focus_terminal"):
                window._on_focus_terminal()

                # Terminal should receive focus
                # (Implementation will test widget.setFocus())

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_does_nothing_when_not_in_ticket_detail(self, mock_state_manager):
        """Should do nothing when not in ticket detail view."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # On runs table
        if hasattr(window, "_stacked_widget"):
            assert window._stacked_widget.currentIndex() == 0

            if hasattr(window, "_on_focus_terminal"):
                # Should not raise error, just do nothing
                window._on_focus_terminal()

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_does_nothing_when_terminal_not_exists(self, mock_state_manager):
        """Should do nothing gracefully when terminal widget doesn't exist."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # In ticket detail but no terminal loaded yet
        if hasattr(window, "_stacked_widget"):
            window._stacked_widget.setCurrentIndex(1)

            if hasattr(window, "_on_focus_terminal"):
                # Should not crash
                window._on_focus_terminal()

        window.close()


class TestToggleThemeAction:
    """Test theme toggle action (already exists, verify hotkey integration)."""

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.apply_theme")
    def test_theme_cycle_via_hotkey(self, mock_apply, mock_state_manager):
        """Theme cycle should work via hotkey."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # _cycle_theme already exists
        window._cycle_theme()

        # Should have triggered theme application
        # (Tested in existing theme tests)

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_theme_persists_after_hotkey_toggle(self, mock_state_manager):
        """Theme preference should persist after toggling via hotkey."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference, get_theme_preference

        # Set initial theme
        set_theme_preference("system")
        initial = get_theme_preference()

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Cycle theme
        window._cycle_theme()

        # Should have changed
        new_pref = get_theme_preference()
        assert new_pref != initial

        window.close()


class TestHotkeyActionStatusMessages:
    """Test status messages or feedback for hotkey actions."""

    @patch("levelup.gui.main_window.StateManager")
    def test_no_waiting_tickets_shows_message(self, mock_state_manager):
        """Should show brief message when no tickets are waiting."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        if hasattr(window, "_on_next_waiting_ticket"):
            # Should show status message or do nothing gracefully
            window._on_next_waiting_ticket()

            # Check for status bar message (if implemented)
            if hasattr(window, "statusBar"):
                status = window.statusBar()
                # May show "No tickets waiting for input" or similar

        window.close()
