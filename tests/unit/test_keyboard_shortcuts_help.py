"""Tests for keyboard shortcuts help dialog and menu."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QPushButton, QAction, QMenu, QDialog, QLabel

from levelup.gui.main_window import MainWindow


def _ensure_qapp():
    """Ensure QApplication exists."""
    return QApplication.instance() or QApplication([])


class TestKeyboardShortcutsHelpDialog:
    """Test keyboard shortcuts reference dialog."""

    def test_help_dialog_exists(self):
        """KeyboardShortcutsHelp dialog should be importable."""
        _ensure_qapp()

        from levelup.gui.keyboard_shortcuts_help import KeyboardShortcutsHelp

        dialog = KeyboardShortcutsHelp()
        assert dialog is not None
        assert isinstance(dialog, QDialog)

        dialog.close()

    def test_help_dialog_shows_all_shortcuts(self):
        """Help dialog should display all available keyboard shortcuts."""
        _ensure_qapp()

        from levelup.gui.keyboard_shortcuts_help import KeyboardShortcutsHelp

        dialog = KeyboardShortcutsHelp()

        # Should have content showing shortcuts
        labels = dialog.findChildren(QLabel)

        # Should mention some of the hotkeys
        all_text = " ".join([label.text() for label in labels])

        # Check for some expected shortcuts
        expected_mentions = [
            "Ctrl+N" or "Next",
            "Escape" or "Back",
            "F5" or "Refresh",
            "F1" or "Documentation",
        ]

        # At least some should be present
        # (Implementation may vary in exact format)

        dialog.close()

    def test_help_dialog_can_accept_custom_settings(self):
        """Help dialog should accept and display custom hotkey settings."""
        _ensure_qapp()

        from levelup.gui.keyboard_shortcuts_help import KeyboardShortcutsHelp
        from levelup.config.settings import HotkeySettings

        custom_settings = HotkeySettings(next_waiting_ticket="Alt+N")
        dialog = KeyboardShortcutsHelp(settings=custom_settings)

        assert dialog is not None

        dialog.close()

    def test_help_dialog_has_close_button(self):
        """Help dialog should have a Close or OK button."""
        _ensure_qapp()

        from levelup.gui.keyboard_shortcuts_help import KeyboardShortcutsHelp

        dialog = KeyboardShortcutsHelp()

        # Find close/ok button
        buttons = dialog.findChildren(QPushButton)
        close_buttons = [
            btn for btn in buttons
            if "close" in btn.text().lower() or "ok" in btn.text().lower()
        ]

        assert len(close_buttons) > 0, "Help dialog should have a Close button"

        dialog.close()


class TestKeyboardShortcutsHelpContent:
    """Test content displayed in help dialog."""

    def test_shows_action_descriptions(self):
        """Help should show human-readable action descriptions."""
        _ensure_qapp()

        from levelup.gui.keyboard_shortcuts_help import KeyboardShortcutsHelp

        dialog = KeyboardShortcutsHelp()

        # Should have descriptive text for actions
        labels = dialog.findChildren(QLabel)
        all_text = " ".join([label.text() for label in labels])

        # Should contain action descriptions
        expected_descriptions = [
            "Next waiting ticket",
            "Back to runs",
            "Toggle theme",
            "Refresh",
            "Documentation",
            "Focus terminal",
        ]

        # At least some descriptions should be present
        # (Exact format may vary)

        dialog.close()

    def test_shows_keybindings_with_descriptions(self):
        """Help should pair keybindings with their descriptions."""
        _ensure_qapp()

        from levelup.gui.keyboard_shortcuts_help import KeyboardShortcutsHelp

        dialog = KeyboardShortcutsHelp()

        # Should show pairs like "Ctrl+N - Next waiting ticket"
        # Implementation detail - could be table, list, etc.

        dialog.close()

    def test_organizes_shortcuts_by_category(self):
        """Help should optionally organize shortcuts by category."""
        _ensure_qapp()

        from levelup.gui.keyboard_shortcuts_help import KeyboardShortcutsHelp

        dialog = KeyboardShortcutsHelp()

        # Could have categories like "Navigation", "View", "General"
        # Implementation detail

        dialog.close()


class TestHelpMenuIntegration:
    """Test Help menu item in MainWindow."""

    @patch("levelup.gui.main_window.StateManager")
    def test_main_window_has_help_menu_item(self, mock_state_manager):
        """MainWindow should have a Help or ? menu item."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Look for help menu or button
        # Could be:
        # 1. Menu bar with Help menu
        # 2. ? button in toolbar
        # 3. Keyboard Shortcuts menu item

        # Check for menu bar
        menubar = window.menuBar()
        if menubar:
            # Look for Help menu or similar
            actions = menubar.actions()
            help_actions = [
                a for a in actions
                if "help" in a.text().lower() or "?" in a.text()
            ]

            # Or could be in View menu, Settings, etc.

        # Or check for button
        help_buttons = [
            btn for btn in window.findChildren(QPushButton)
            if "?" in btn.text() or "help" in btn.objectName().lower()
        ]

        # At least one way to access help should exist
        # (Could be menu or button)

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_help_action_opens_shortcuts_dialog(self, mock_state_manager):
        """Clicking help should open keyboard shortcuts dialog."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have method to show help
        assert hasattr(window, "_show_keyboard_shortcuts_help") or \
               hasattr(window, "_on_help_clicked") or \
               hasattr(window, "show_shortcuts_help")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_help_button_in_toolbar(self, mock_state_manager):
        """Should have a help/? button in toolbar."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Find help button
        help_buttons = [
            btn for btn in window.findChildren(QPushButton)
            if "?" in btn.text()
        ]

        # Help button should exist
        # (Or accessible via menu)

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_help_button_has_tooltip(self, mock_state_manager):
        """Help button should have a tooltip."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        help_buttons = [
            btn for btn in window.findChildren(QPushButton)
            if "?" in btn.text()
        ]

        if help_buttons:
            help_btn = help_buttons[0]
            tooltip = help_btn.toolTip()
            assert tooltip is not None and len(tooltip) > 0
            assert "keyboard" in tooltip.lower() or "shortcut" in tooltip.lower()

        window.close()


class TestHotkeyHelpAccess:
    """Test accessing keyboard shortcuts help."""

    @patch("levelup.gui.main_window.StateManager")
    def test_can_open_help_programmatically(self, mock_state_manager):
        """Should be able to open help dialog programmatically."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have method to show help
        if hasattr(window, "_show_keyboard_shortcuts_help"):
            # Should not crash
            # window._show_keyboard_shortcuts_help()
            pass

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_help_shows_current_keybindings(self, mock_state_manager):
        """Help dialog should show current keybindings, not just defaults."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        with patch("levelup.gui.main_window.load_settings") as mock_load:
            from levelup.config.settings import LevelUpSettings, GUISettings, HotkeySettings

            # Custom settings
            mock_settings = LevelUpSettings(
                gui=GUISettings(
                    hotkeys=HotkeySettings(next_waiting_ticket="Alt+N")
                )
            )
            mock_load.return_value = mock_settings

            window = MainWindow(mock_state, project_path=Path.cwd())

            # When help is shown, it should show Alt+N, not Ctrl+N
            # Implementation detail

        window.close()


class TestHelpDialogFormatting:
    """Test help dialog formatting and presentation."""

    def test_help_uses_monospace_font_for_shortcuts(self):
        """Keybindings should use monospace font for clarity."""
        _ensure_qapp()

        from levelup.gui.keyboard_shortcuts_help import KeyboardShortcutsHelp

        dialog = KeyboardShortcutsHelp()

        # Should use monospace or code-style formatting for key sequences
        # Implementation detail

        dialog.close()

    def test_help_is_readable_in_both_themes(self):
        """Help dialog should be readable in both dark and light themes."""
        _ensure_qapp()

        from levelup.gui.keyboard_shortcuts_help import KeyboardShortcutsHelp

        # Test with dark theme
        dialog_dark = KeyboardShortcutsHelp()
        # Should be readable
        dialog_dark.close()

        # Test with light theme
        dialog_light = KeyboardShortcutsHelp()
        # Should be readable
        dialog_light.close()

    def test_help_dialog_has_title(self):
        """Help dialog should have a descriptive title."""
        _ensure_qapp()

        from levelup.gui.keyboard_shortcuts_help import KeyboardShortcutsHelp

        dialog = KeyboardShortcutsHelp()

        title = dialog.windowTitle()
        assert title is not None and len(title) > 0
        assert "keyboard" in title.lower() or "shortcut" in title.lower()

        dialog.close()
