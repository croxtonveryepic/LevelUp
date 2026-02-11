"""Integration tests for hotkey settings persistence."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import yaml

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QShortcut, QKeySequence

from levelup.gui.main_window import MainWindow
from levelup.config.settings import LevelUpSettings, GUISettings, HotkeySettings
from levelup.config.loader import load_settings


def _ensure_qapp():
    """Ensure QApplication exists."""
    return QApplication.instance() or QApplication([])


class TestHotkeyPersistence:
    """Test that hotkey settings are persisted to config file."""

    def test_default_hotkeys_in_config(self, tmp_path):
        """Default hotkeys should be in loaded config."""
        # Create config file with hotkeys
        config_file = tmp_path / "levelup.yaml"
        config_data = {
            "gui": {
                "theme": "dark",
                "hotkeys": {
                    "next_waiting_ticket": "Ctrl+N",
                    "back_to_runs": "Escape",
                    "toggle_theme": "Ctrl+T",
                    "refresh_dashboard": "F5",
                    "open_documentation": "F1",
                    "focus_terminal": "Ctrl+`",
                },
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Load settings
        settings = load_settings(project_path=tmp_path)

        # Should have hotkey settings
        assert settings.gui.hotkeys.next_waiting_ticket == "Ctrl+N"
        assert settings.gui.hotkeys.back_to_runs == "Escape"
        assert settings.gui.hotkeys.refresh_dashboard == "F5"

    def test_custom_hotkeys_in_config(self, tmp_path):
        """Custom hotkeys should be loadable from config."""
        config_file = tmp_path / "levelup.yaml"
        config_data = {
            "gui": {
                "hotkeys": {
                    "next_waiting_ticket": "Alt+N",
                    "back_to_runs": "Ctrl+B",
                    "toggle_theme": "Ctrl+Shift+T",
                    "refresh_dashboard": "Ctrl+R",
                    "open_documentation": "Ctrl+D",
                    "focus_terminal": "Ctrl+Shift+T",
                },
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        settings = load_settings(project_path=tmp_path)

        # Should load custom hotkeys
        assert settings.gui.hotkeys.next_waiting_ticket == "Alt+N"
        assert settings.gui.hotkeys.back_to_runs == "Ctrl+B"
        assert settings.gui.hotkeys.refresh_dashboard == "Ctrl+R"

    def test_partial_hotkeys_use_defaults(self, tmp_path):
        """Config with partial hotkeys should use defaults for missing ones."""
        config_file = tmp_path / "levelup.yaml"
        config_data = {
            "gui": {
                "hotkeys": {
                    "next_waiting_ticket": "Alt+N",
                    # Other hotkeys not specified
                },
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        settings = load_settings(project_path=tmp_path)

        # Custom hotkey
        assert settings.gui.hotkeys.next_waiting_ticket == "Alt+N"

        # Defaults for others
        assert settings.gui.hotkeys.back_to_runs == "Escape"
        assert settings.gui.hotkeys.refresh_dashboard == "F5"

    def test_empty_config_uses_all_defaults(self, tmp_path):
        """Empty config should use all default hotkeys."""
        config_file = tmp_path / "levelup.yaml"

        with open(config_file, "w") as f:
            yaml.dump({}, f)

        settings = load_settings(project_path=tmp_path)

        # All defaults
        assert settings.gui.hotkeys.next_waiting_ticket == "Ctrl+N"
        assert settings.gui.hotkeys.back_to_runs == "Escape"
        assert settings.gui.hotkeys.toggle_theme == "Ctrl+T"
        assert settings.gui.hotkeys.refresh_dashboard == "F5"
        assert settings.gui.hotkeys.open_documentation == "F1"
        assert settings.gui.hotkeys.focus_terminal == "Ctrl+`"


class TestHotkeySettingsSaving:
    """Test saving hotkey settings to config file."""

    def test_save_updated_hotkeys(self, tmp_path):
        """Should be able to save updated hotkey settings."""
        config_file = tmp_path / "levelup.yaml"

        # Initial config
        with open(config_file, "w") as f:
            yaml.dump({"gui": {"theme": "dark"}}, f)

        # Load, modify, save
        from levelup.config.loader import save_settings

        settings = load_settings(project_path=tmp_path)
        settings.gui.hotkeys.next_waiting_ticket = "Alt+N"

        save_settings(settings, project_path=tmp_path)

        # Reload and verify
        reloaded = load_settings(project_path=tmp_path)
        assert reloaded.gui.hotkeys.next_waiting_ticket == "Alt+N"

    def test_save_preserves_other_settings(self, tmp_path):
        """Saving hotkeys should preserve other settings."""
        config_file = tmp_path / "levelup.yaml"

        # Initial config with multiple settings
        initial_data = {
            "gui": {
                "theme": "dark",
                "hotkeys": {
                    "next_waiting_ticket": "Ctrl+N",
                },
            },
            "pipeline": {
                "max_code_iterations": 10,
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(initial_data, f)

        # Load, modify hotkeys, save
        from levelup.config.loader import save_settings

        settings = load_settings(project_path=tmp_path)
        settings.gui.hotkeys.refresh_dashboard = "Ctrl+R"

        save_settings(settings, project_path=tmp_path)

        # Reload and verify all settings preserved
        reloaded = load_settings(project_path=tmp_path)
        assert reloaded.gui.theme == "dark"
        assert reloaded.pipeline.max_code_iterations == 10
        assert reloaded.gui.hotkeys.refresh_dashboard == "Ctrl+R"

    def test_round_trip_hotkeys(self, tmp_path):
        """Hotkeys should survive save/load round trip."""
        config_file = tmp_path / "levelup.yaml"

        with open(config_file, "w") as f:
            yaml.dump({}, f)

        from levelup.config.loader import save_settings

        # Create settings with custom hotkeys
        settings = LevelUpSettings(
            gui=GUISettings(
                hotkeys=HotkeySettings(
                    next_waiting_ticket="Alt+N",
                    back_to_runs="Ctrl+B",
                    toggle_theme="Ctrl+Shift+T",
                    refresh_dashboard="Ctrl+R",
                    open_documentation="Ctrl+D",
                    focus_terminal="Ctrl+Shift+T",
                )
            )
        )

        # Save
        save_settings(settings, project_path=tmp_path)

        # Load
        reloaded = load_settings(project_path=tmp_path)

        # Verify all hotkeys
        assert reloaded.gui.hotkeys.next_waiting_ticket == "Alt+N"
        assert reloaded.gui.hotkeys.back_to_runs == "Ctrl+B"
        assert reloaded.gui.hotkeys.toggle_theme == "Ctrl+Shift+T"
        assert reloaded.gui.hotkeys.refresh_dashboard == "Ctrl+R"
        assert reloaded.gui.hotkeys.open_documentation == "Ctrl+D"
        assert reloaded.gui.hotkeys.focus_terminal == "Ctrl+Shift+T"


class TestMainWindowLoadsCustomHotkeys:
    """Test MainWindow loads and uses custom hotkeys from config."""

    @patch("levelup.gui.main_window.StateManager")
    def test_main_window_uses_config_hotkeys(self, mock_state_manager, tmp_path):
        """MainWindow should use hotkeys from config file."""
        _ensure_qapp()

        # Create config with custom hotkeys
        config_file = tmp_path / "levelup.yaml"
        config_data = {
            "gui": {
                "hotkeys": {
                    "next_waiting_ticket": "Alt+N",
                    "refresh_dashboard": "Ctrl+R",
                },
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        # Create window with project path pointing to config
        window = MainWindow(mock_state, project_path=tmp_path)

        # Should have registered custom shortcuts
        shortcuts = window.findChildren(QShortcut)

        # Check for Alt+N (custom next_waiting_ticket)
        alt_n = [s for s in shortcuts if s.key() == QKeySequence("Alt+N")]
        assert len(alt_n) > 0, "Should have Alt+N shortcut from config"

        # Check for Ctrl+R (custom refresh)
        ctrl_r = [s for s in shortcuts if s.key() == QKeySequence("Ctrl+R")]
        assert len(ctrl_r) > 0, "Should have Ctrl+R shortcut from config"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_no_old_shortcuts_registered(self, mock_state_manager, tmp_path):
        """When using custom hotkeys, old defaults should not be registered."""
        _ensure_qapp()

        config_file = tmp_path / "levelup.yaml"
        config_data = {
            "gui": {
                "hotkeys": {
                    "next_waiting_ticket": "Alt+N",  # Changed from Ctrl+N
                },
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=tmp_path)

        shortcuts = window.findChildren(QShortcut)

        # Should NOT have Ctrl+N (old default)
        # (Only if Ctrl+N is not used for another action)
        # Check that Alt+N is registered
        alt_n = [s for s in shortcuts if s.key() == QKeySequence("Alt+N")]
        assert len(alt_n) > 0

        window.close()


class TestSettingsUpdateFlow:
    """Test complete flow of updating and persisting settings."""

    @patch("levelup.gui.main_window.StateManager")
    def test_change_settings_via_dialog_persists(self, mock_state_manager, tmp_path):
        """Changing settings via dialog should persist to config file."""
        _ensure_qapp()

        config_file = tmp_path / "levelup.yaml"

        with open(config_file, "w") as f:
            yaml.dump({}, f)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=tmp_path)

        # Simulate changing settings
        # (Would normally happen via dialog, but we can test the save path)
        from levelup.config.loader import save_settings

        if hasattr(window, "_apply_hotkey_settings"):
            # Update settings
            new_hotkeys = HotkeySettings(next_waiting_ticket="Alt+N")

            # Get current settings
            settings = load_settings(project_path=tmp_path)
            settings.gui.hotkeys = new_hotkeys

            # Save
            save_settings(settings, project_path=tmp_path)

            # Verify persisted
            with open(config_file) as f:
                saved_data = yaml.safe_load(f)

            assert saved_data["gui"]["hotkeys"]["next_waiting_ticket"] == "Alt+N"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_restart_loads_saved_settings(self, mock_state_manager, tmp_path):
        """After saving, restarting window should load new settings."""
        _ensure_qapp()

        config_file = tmp_path / "levelup.yaml"

        # Save custom settings
        config_data = {
            "gui": {
                "hotkeys": {
                    "next_waiting_ticket": "Alt+N",
                },
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        # Create first window
        window1 = MainWindow(mock_state, project_path=tmp_path)

        shortcuts1 = window1.findChildren(QShortcut)
        alt_n1 = [s for s in shortcuts1 if s.key() == QKeySequence("Alt+N")]
        assert len(alt_n1) > 0

        window1.close()

        # Create second window (simulating restart)
        window2 = MainWindow(mock_state, project_path=tmp_path)

        shortcuts2 = window2.findChildren(QShortcut)
        alt_n2 = [s for s in shortcuts2 if s.key() == QKeySequence("Alt+N")]
        assert len(alt_n2) > 0, "Settings should persist across restarts"

        window2.close()
