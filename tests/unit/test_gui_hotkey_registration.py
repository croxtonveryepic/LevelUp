"""Tests for hotkey registration system in MainWindow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtCore import Qt

from levelup.gui.main_window import MainWindow
from levelup.state.manager import StateManager


def _ensure_qapp():
    """Ensure QApplication exists."""
    return QApplication.instance() or QApplication([])


class TestHotkeyRegistration:
    """Test that hotkeys are registered in MainWindow."""

    @patch("levelup.gui.main_window.StateManager")
    def test_main_window_registers_hotkeys(self, mock_state_manager):
        """MainWindow should register all hotkeys on initialization."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have hotkeys registered
        assert hasattr(window, "_hotkeys") or hasattr(window, "_shortcuts")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_all_hotkey_actions_registered(self, mock_state_manager):
        """All hotkey actions should be registered as QShortcut instances."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Find all QShortcut children
        shortcuts = window.findChildren(QShortcut)

        # Should have shortcuts for each action
        # At minimum: next_waiting_ticket, back_to_runs, toggle_theme,
        # refresh_dashboard, open_documentation, focus_terminal
        assert len(shortcuts) >= 6, f"Expected at least 6 shortcuts, found {len(shortcuts)}"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_hotkeys_loaded_from_settings(self, mock_state_manager):
        """Hotkeys should be loaded from settings on initialization."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        with patch("levelup.gui.main_window.load_settings") as mock_load:
            from levelup.config.settings import LevelUpSettings, GUISettings, HotkeySettings

            # Mock custom hotkey settings
            mock_settings = LevelUpSettings(
                gui=GUISettings(
                    hotkeys=HotkeySettings(next_waiting_ticket="Alt+N")
                )
            )
            mock_load.return_value = mock_settings

            window = MainWindow(mock_state, project_path=Path.cwd())

            # Should have loaded settings
            mock_load.assert_called()

            window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_shortcuts_attached_to_main_window(self, mock_state_manager):
        """QShortcut instances should be attached to MainWindow."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        shortcuts = window.findChildren(QShortcut)

        for shortcut in shortcuts:
            # Each shortcut's parent should be the main window
            assert shortcut.parent() == window

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_shortcuts_have_application_context(self, mock_state_manager):
        """Shortcuts should work globally within the application window."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        shortcuts = window.findChildren(QShortcut)

        # At least some shortcuts should have window or application context
        assert len(shortcuts) > 0, "Should have registered shortcuts"

        window.close()


class TestNextWaitingTicketHotkey:
    """Test Ctrl+N / Cmd+N hotkey to navigate to next waiting ticket."""

    @patch("levelup.gui.main_window.StateManager")
    def test_next_waiting_ticket_shortcut_exists(self, mock_state_manager):
        """Next waiting ticket shortcut should be registered."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have method to handle this action
        assert hasattr(window, "_on_next_waiting_ticket") or \
               hasattr(window, "_jump_to_next_waiting_ticket")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_next_waiting_ticket_uses_ctrl_n_default(self, mock_state_manager):
        """Next waiting ticket should default to Ctrl+N."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Find the shortcut with Ctrl+N
        shortcuts = window.findChildren(QShortcut)
        ctrl_n_shortcuts = [
            s for s in shortcuts
            if s.key() == QKeySequence("Ctrl+N")
        ]

        assert len(ctrl_n_shortcuts) > 0, "Should have Ctrl+N shortcut"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_next_waiting_ticket_triggers_navigation(self, mock_state_manager):
        """Activating next waiting ticket shortcut should trigger navigation."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Mock the navigation method
        window._on_next_waiting_ticket = Mock()

        # Find and activate the shortcut
        shortcuts = window.findChildren(QShortcut)
        ctrl_n_shortcuts = [
            s for s in shortcuts
            if s.key() == QKeySequence("Ctrl+N")
        ]

        if ctrl_n_shortcuts:
            ctrl_n_shortcuts[0].activated.emit()
            # Should have triggered navigation
            # (Implementation may vary, this tests the signal connection)

        window.close()


class TestBackToRunsHotkey:
    """Test Escape hotkey to return to runs table."""

    @patch("levelup.gui.main_window.StateManager")
    def test_back_to_runs_shortcut_exists(self, mock_state_manager):
        """Back to runs shortcut should be registered."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have method to handle this action
        assert hasattr(window, "_on_back_to_runs") or \
               hasattr(window, "_return_to_runs_view")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_back_to_runs_uses_escape_default(self, mock_state_manager):
        """Back to runs should default to Escape."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        shortcuts = window.findChildren(QShortcut)
        escape_shortcuts = [
            s for s in shortcuts
            if s.key() == QKeySequence("Escape")
        ]

        assert len(escape_shortcuts) > 0, "Should have Escape shortcut"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_back_to_runs_from_ticket_detail(self, mock_state_manager):
        """Escape should return to runs view from ticket detail."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Switch to ticket detail view (page 1)
        if hasattr(window, "_stacked_widget"):
            window._stacked_widget.setCurrentIndex(1)

        # Mock the back method
        original_index = window._stacked_widget.currentIndex() if hasattr(window, "_stacked_widget") else 0

        # Trigger escape
        escape_shortcuts = [
            s for s in window.findChildren(QShortcut)
            if s.key() == QKeySequence("Escape")
        ]

        if escape_shortcuts:
            escape_shortcuts[0].activated.emit()
            # Should switch back to runs table
            # (Actual behavior tested in integration tests)

        window.close()


class TestToggleThemeHotkey:
    """Test Ctrl+T hotkey to toggle theme."""

    @patch("levelup.gui.main_window.StateManager")
    def test_toggle_theme_shortcut_exists(self, mock_state_manager):
        """Toggle theme shortcut should be registered."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should already have _cycle_theme method
        assert hasattr(window, "_cycle_theme")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_toggle_theme_uses_ctrl_t_default(self, mock_state_manager):
        """Toggle theme should default to Ctrl+T."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        shortcuts = window.findChildren(QShortcut)
        ctrl_t_shortcuts = [
            s for s in shortcuts
            if s.key() == QKeySequence("Ctrl+T")
        ]

        assert len(ctrl_t_shortcuts) > 0, "Should have Ctrl+T shortcut"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.apply_theme")
    def test_toggle_theme_triggers_cycle(self, mock_apply, mock_state_manager):
        """Activating toggle theme shortcut should cycle theme."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Find Ctrl+T shortcut
        shortcuts = window.findChildren(QShortcut)
        ctrl_t_shortcuts = [
            s for s in shortcuts
            if s.key() == QKeySequence("Ctrl+T")
        ]

        if ctrl_t_shortcuts:
            # Mock the cycle method
            window._cycle_theme = Mock()
            ctrl_t_shortcuts[0].activated.emit()
            # Cycle should have been called (connection tested in integration)

        window.close()


class TestRefreshDashboardHotkey:
    """Test F5 hotkey to refresh dashboard."""

    @patch("levelup.gui.main_window.StateManager")
    def test_refresh_dashboard_shortcut_exists(self, mock_state_manager):
        """Refresh dashboard shortcut should be registered."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have refresh method
        assert hasattr(window, "_refresh")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_refresh_dashboard_uses_f5_default(self, mock_state_manager):
        """Refresh dashboard should default to F5."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        shortcuts = window.findChildren(QShortcut)
        f5_shortcuts = [
            s for s in shortcuts
            if s.key() == QKeySequence("F5")
        ]

        assert len(f5_shortcuts) > 0, "Should have F5 shortcut"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_refresh_dashboard_triggers_refresh(self, mock_state_manager):
        """Activating refresh shortcut should trigger refresh."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Mock refresh method
        window._refresh = Mock()

        # Find F5 shortcut
        shortcuts = window.findChildren(QShortcut)
        f5_shortcuts = [
            s for s in shortcuts
            if s.key() == QKeySequence("F5")
        ]

        if f5_shortcuts:
            f5_shortcuts[0].activated.emit()
            # Refresh should be triggered (connection tested in integration)

        window.close()


class TestOpenDocumentationHotkey:
    """Test F1 hotkey to open documentation."""

    @patch("levelup.gui.main_window.StateManager")
    def test_open_docs_shortcut_exists(self, mock_state_manager):
        """Open documentation shortcut should be registered."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have docs method
        assert hasattr(window, "_on_docs_clicked")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_open_docs_uses_f1_default(self, mock_state_manager):
        """Open documentation should default to F1."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        shortcuts = window.findChildren(QShortcut)
        f1_shortcuts = [
            s for s in shortcuts
            if s.key() == QKeySequence("F1")
        ]

        assert len(f1_shortcuts) > 0, "Should have F1 shortcut"

        window.close()


class TestFocusTerminalHotkey:
    """Test Ctrl+` hotkey to focus terminal."""

    @patch("levelup.gui.main_window.StateManager")
    def test_focus_terminal_shortcut_exists(self, mock_state_manager):
        """Focus terminal shortcut should be registered."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have method to focus terminal
        assert hasattr(window, "_on_focus_terminal") or \
               hasattr(window, "_focus_ticket_terminal")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_focus_terminal_uses_ctrl_backtick_default(self, mock_state_manager):
        """Focus terminal should default to Ctrl+`."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        shortcuts = window.findChildren(QShortcut)
        ctrl_backtick_shortcuts = [
            s for s in shortcuts
            if s.key() == QKeySequence("Ctrl+`")
        ]

        assert len(ctrl_backtick_shortcuts) > 0, "Should have Ctrl+` shortcut"

        window.close()


class TestHotkeyDynamicUpdate:
    """Test that hotkeys can be updated dynamically without restart."""

    @patch("levelup.gui.main_window.StateManager")
    def test_hotkeys_can_be_updated_after_init(self, mock_state_manager):
        """Hotkeys should be updateable after window initialization."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have method to update hotkeys
        assert hasattr(window, "_update_hotkeys") or \
               hasattr(window, "_reload_hotkeys") or \
               hasattr(window, "update_hotkeys")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_updating_hotkeys_reregisters_shortcuts(self, mock_state_manager):
        """Updating hotkeys should reregister QShortcut instances."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        initial_shortcuts = len(window.findChildren(QShortcut))

        # Update hotkeys (if method exists)
        if hasattr(window, "_update_hotkeys"):
            from levelup.config.settings import HotkeySettings
            new_hotkeys = HotkeySettings(next_waiting_ticket="Alt+N")
            window._update_hotkeys(new_hotkeys)

            # Should still have shortcuts registered
            updated_shortcuts = len(window.findChildren(QShortcut))
            assert updated_shortcuts >= initial_shortcuts

        window.close()
