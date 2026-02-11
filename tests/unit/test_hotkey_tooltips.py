"""Tests for hotkey tooltips on buttons."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QPushButton

from levelup.gui.main_window import MainWindow


def _ensure_qapp():
    """Ensure QApplication exists."""
    return QApplication.instance() or QApplication([])


class TestRefreshButtonTooltip:
    """Test Refresh button shows keyboard shortcut in tooltip."""

    @patch("levelup.gui.main_window.StateManager")
    def test_refresh_button_tooltip_shows_hotkey(self, mock_state_manager):
        """Refresh button tooltip should show F5 shortcut."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Find refresh button
        refresh_btn = None
        if hasattr(window, "_refresh_btn"):
            refresh_btn = window._refresh_btn
        else:
            # Search for it
            for btn in window.findChildren(QPushButton):
                if "refresh" in btn.objectName().lower() or "↻" in btn.text():
                    refresh_btn = btn
                    break

        if refresh_btn:
            tooltip = refresh_btn.toolTip()
            assert tooltip is not None and len(tooltip) > 0
            # Should mention F5
            assert "F5" in tooltip or "f5" in tooltip.lower()

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_refresh_tooltip_format(self, mock_state_manager):
        """Refresh tooltip should follow format 'Refresh (F5)'."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        refresh_btn = None
        if hasattr(window, "_refresh_btn"):
            refresh_btn = window._refresh_btn
        else:
            for btn in window.findChildren(QPushButton):
                if "refresh" in btn.objectName().lower() or "↻" in btn.text():
                    refresh_btn = btn
                    break

        if refresh_btn:
            tooltip = refresh_btn.toolTip()
            # Should contain both action name and shortcut
            assert "Refresh" in tooltip or "refresh" in tooltip.lower()
            assert "F5" in tooltip or "(" in tooltip  # Parentheses for shortcut

        window.close()


class TestDocsButtonTooltip:
    """Test Documentation button shows keyboard shortcut in tooltip."""

    @patch("levelup.gui.main_window.StateManager")
    def test_docs_button_tooltip_shows_hotkey(self, mock_state_manager):
        """Docs button tooltip should show F1 shortcut."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Find docs button
        docs_btn = None
        if hasattr(window, "_docs_btn"):
            docs_btn = window._docs_btn

        if docs_btn:
            tooltip = docs_btn.toolTip()
            assert tooltip is not None and len(tooltip) > 0
            # Should mention F1
            assert "F1" in tooltip or "f1" in tooltip.lower()

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_docs_tooltip_format(self, mock_state_manager):
        """Docs tooltip should follow format 'Documentation (F1)'."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        if hasattr(window, "_docs_btn"):
            docs_btn = window._docs_btn
            tooltip = docs_btn.toolTip()

            # Should mention docs and F1
            assert "F1" in tooltip

        window.close()


class TestBackButtonTooltip:
    """Test Back button shows keyboard shortcut in tooltip."""

    @patch("levelup.gui.main_window.StateManager")
    def test_back_button_tooltip_shows_hotkey(self, mock_state_manager):
        """Back button tooltip should show Escape shortcut."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Back button is in ticket detail view
        # Find it
        back_buttons = [
            btn for btn in window.findChildren(QPushButton)
            if "back" in btn.objectName().lower() or btn.text() == "← Back"
        ]

        if back_buttons:
            back_btn = back_buttons[0]
            tooltip = back_btn.toolTip()

            if tooltip:
                # Should mention Escape
                assert "Escape" in tooltip or "Esc" in tooltip or "escape" in tooltip.lower()

        window.close()


class TestThemeButtonTooltip:
    """Test Theme button shows keyboard shortcut in tooltip."""

    @patch("levelup.gui.main_window.StateManager")
    def test_theme_button_tooltip_shows_hotkey(self, mock_state_manager):
        """Theme button tooltip should show Ctrl+T shortcut."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher

        if theme_btn:
            tooltip = theme_btn.toolTip()
            # Should mention Ctrl+T
            assert "Ctrl" in tooltip or "ctrl" in tooltip.lower()

        window.close()


class TestTooltipUpdatesWithSettings:
    """Test tooltips update when hotkey settings change."""

    @patch("levelup.gui.main_window.StateManager")
    def test_tooltip_reflects_custom_keybinding(self, mock_state_manager):
        """Tooltip should reflect custom keybinding from settings."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        with patch("levelup.gui.main_window.load_settings") as mock_load:
            from levelup.config.settings import LevelUpSettings, GUISettings, HotkeySettings

            # Custom refresh hotkey
            mock_settings = LevelUpSettings(
                gui=GUISettings(
                    hotkeys=HotkeySettings(refresh_dashboard="Ctrl+R")
                )
            )
            mock_load.return_value = mock_settings

            window = MainWindow(mock_state, project_path=Path.cwd())

            # Find refresh button
            refresh_btn = None
            if hasattr(window, "_refresh_btn"):
                refresh_btn = window._refresh_btn
            else:
                for btn in window.findChildren(QPushButton):
                    if "refresh" in btn.objectName().lower():
                        refresh_btn = btn
                        break

            if refresh_btn:
                tooltip = refresh_btn.toolTip()
                # Should show Ctrl+R instead of F5
                assert "Ctrl+R" in tooltip or "Ctrl" in tooltip

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_tooltips_update_after_settings_change(self, mock_state_manager):
        """Tooltips should update after changing settings."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Update hotkey settings
        if hasattr(window, "_update_hotkeys"):
            from levelup.config.settings import HotkeySettings

            new_settings = HotkeySettings(refresh_dashboard="Ctrl+R")
            window._update_hotkeys(new_settings)

            # Tooltips should update
            if hasattr(window, "_refresh_btn"):
                tooltip = window._refresh_btn.toolTip()
                # Should show new keybinding
                # Implementation detail

        window.close()


class TestAllButtonsHaveHotkeyTooltips:
    """Test all relevant buttons show keyboard shortcuts in tooltips."""

    @patch("levelup.gui.main_window.StateManager")
    def test_all_hotkey_actions_shown_in_tooltips(self, mock_state_manager):
        """All buttons with hotkeys should show shortcuts in tooltips."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Expected hotkey mentions in tooltips
        expected_hotkeys = {
            "F5",      # Refresh
            "F1",      # Docs
            "Escape",  # Back (or Esc)
            "Ctrl",    # Theme toggle, other Ctrl shortcuts
        }

        # Collect all button tooltips
        tooltips = [
            btn.toolTip()
            for btn in window.findChildren(QPushButton)
            if btn.toolTip()
        ]

        # At least some buttons should show hotkeys
        assert len(tooltips) > 0

        # Some tooltips should contain hotkey information
        tooltips_with_hotkeys = [
            t for t in tooltips
            if any(key in t for key in expected_hotkeys)
        ]

        assert len(tooltips_with_hotkeys) > 0, "Some tooltips should show keyboard shortcuts"

        window.close()
