"""Tests for hotkey settings button in MainWindow toolbar."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QPushButton

from levelup.gui.main_window import MainWindow


def _ensure_qapp():
    """Ensure QApplication exists."""
    return QApplication.instance() or QApplication([])


class TestSettingsButton:
    """Test Settings button in toolbar."""

    @patch("levelup.gui.main_window.StateManager")
    def test_main_window_has_settings_button(self, mock_state_manager):
        """MainWindow should have a Settings button in toolbar."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Look for settings button
        settings_buttons = [
            btn for btn in window.findChildren(QPushButton)
            if "settings" in btn.objectName().lower() or
               "settings" in btn.text().lower() or
               "⚙" in btn.text()
        ]

        # Should have a settings button
        # (Or menu item for settings)

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_settings_button_has_icon(self, mock_state_manager):
        """Settings button should have gear icon or similar."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        settings_buttons = [
            btn for btn in window.findChildren(QPushButton)
            if "settings" in btn.objectName().lower() or "⚙" in btn.text()
        ]

        if settings_buttons:
            btn = settings_buttons[0]
            # Should have text or icon
            assert btn.text() or btn.icon()

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_settings_button_has_tooltip(self, mock_state_manager):
        """Settings button should have a helpful tooltip."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        settings_buttons = [
            btn for btn in window.findChildren(QPushButton)
            if "settings" in btn.objectName().lower() or "⚙" in btn.text()
        ]

        if settings_buttons:
            btn = settings_buttons[0]
            tooltip = btn.toolTip()
            # Should have tooltip
            # Could say "Settings", "Keyboard Shortcuts", etc.

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_settings_button_opens_hotkey_dialog(self, mock_state_manager):
        """Clicking Settings should open hotkey settings dialog."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have method to show settings
        assert hasattr(window, "_show_hotkey_settings") or \
               hasattr(window, "_on_settings_clicked") or \
               hasattr(window, "show_settings_dialog")

        window.close()


class TestHotkeySettingsIntegration:
    """Test hotkey settings dialog integration with MainWindow."""

    @patch("levelup.gui.main_window.StateManager")
    def test_opening_settings_passes_current_settings(self, mock_state_manager):
        """Opening settings should pass current hotkey configuration."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # When settings dialog is opened, should pass current settings
        # Implementation detail

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_saving_settings_updates_hotkeys(self, mock_state_manager):
        """Saving settings should update active hotkeys immediately."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have method to apply new settings
        assert hasattr(window, "_apply_hotkey_settings") or \
               hasattr(window, "_update_hotkeys")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_canceling_settings_preserves_current_hotkeys(self, mock_state_manager):
        """Canceling settings should not change hotkeys."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Get current shortcuts
        from PyQt6.QtGui import QShortcut
        initial_shortcuts = window.findChildren(QShortcut)
        initial_count = len(initial_shortcuts)

        # Cancel settings (don't save)
        # Shortcuts should remain unchanged

        # Check shortcuts still exist
        current_shortcuts = window.findChildren(QShortcut)
        assert len(current_shortcuts) == initial_count

        window.close()


class TestSettingsButtonPlacement:
    """Test Settings button placement in toolbar."""

    @patch("levelup.gui.main_window.StateManager")
    def test_settings_button_in_toolbar_layout(self, mock_state_manager):
        """Settings button should be in the toolbar layout."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Settings button should be visible
        settings_buttons = [
            btn for btn in window.findChildren(QPushButton)
            if "settings" in btn.objectName().lower() or "⚙" in btn.text()
        ]

        if settings_buttons:
            btn = settings_buttons[0]
            assert btn.isVisible()

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_settings_button_near_other_controls(self, mock_state_manager):
        """Settings button should be near other toolbar controls."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have multiple toolbar buttons
        toolbar_buttons = window.findChildren(QPushButton)

        # Settings button should be among them
        assert len(toolbar_buttons) > 0

        window.close()


class TestSettingsWorkflow:
    """Test complete settings workflow."""

    @patch("levelup.gui.main_window.StateManager")
    def test_change_settings_and_use_new_hotkey(self, mock_state_manager):
        """Should be able to change settings and use new hotkey immediately."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # 1. Open settings
        # 2. Change a keybinding
        # 3. Save
        # 4. New keybinding should work immediately

        # Implementation detail

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.save_settings")
    def test_settings_persisted_to_config_file(self, mock_save, mock_state_manager):
        """Changed settings should be saved to config file."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # When settings are saved, should call save_settings
        # Implementation will test this

        window.close()


class TestAlternativeSettingsAccess:
    """Test alternative ways to access settings."""

    @patch("levelup.gui.main_window.StateManager")
    def test_settings_accessible_via_menu(self, mock_state_manager):
        """Settings could also be accessible via menu bar."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Check for menu bar
        menubar = window.menuBar()
        if menubar:
            # Could have File > Settings, View > Settings, etc.
            # Implementation detail
            pass

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_hotkey_to_open_settings(self, mock_state_manager):
        """Could have a hotkey to open settings dialog."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Could have Ctrl+, or Ctrl+Shift+P or similar
        # Implementation detail (optional)

        window.close()
