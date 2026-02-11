"""Tests for hotkey settings data model in config/settings.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from levelup.config.settings import HotkeySettings, GUISettings, LevelUpSettings


class TestHotkeySettingsDefaults:
    """Test default keybinding values."""

    def test_hotkey_settings_has_default_keybindings(self):
        """HotkeySettings should have default keybindings for all navigation actions."""
        settings = HotkeySettings()

        # All hotkey actions should have defaults
        assert hasattr(settings, "next_waiting_ticket")
        assert hasattr(settings, "back_to_runs")
        assert hasattr(settings, "toggle_theme")
        assert hasattr(settings, "refresh_dashboard")
        assert hasattr(settings, "open_documentation")
        assert hasattr(settings, "focus_terminal")

    def test_next_waiting_ticket_default(self):
        """Next waiting ticket hotkey should default to Ctrl+N."""
        settings = HotkeySettings()
        assert settings.next_waiting_ticket == "Ctrl+N"

    def test_back_to_runs_default(self):
        """Back to runs hotkey should default to Escape."""
        settings = HotkeySettings()
        assert settings.back_to_runs == "Escape"

    def test_toggle_theme_default(self):
        """Toggle theme hotkey should default to Ctrl+T."""
        settings = HotkeySettings()
        assert settings.toggle_theme == "Ctrl+T"

    def test_refresh_dashboard_default(self):
        """Refresh dashboard hotkey should default to F5."""
        settings = HotkeySettings()
        assert settings.refresh_dashboard == "F5"

    def test_open_documentation_default(self):
        """Open documentation hotkey should default to F1."""
        settings = HotkeySettings()
        assert settings.open_documentation == "F1"

    def test_focus_terminal_default(self):
        """Focus terminal hotkey should default to Ctrl+`."""
        settings = HotkeySettings()
        assert settings.focus_terminal == "Ctrl+`"


class TestHotkeySettingsCustomization:
    """Test customizing keybindings."""

    def test_can_override_single_keybinding(self):
        """Should be able to override a single keybinding."""
        settings = HotkeySettings(next_waiting_ticket="Ctrl+Shift+N")
        assert settings.next_waiting_ticket == "Ctrl+Shift+N"
        # Other defaults should remain
        assert settings.back_to_runs == "Escape"

    def test_can_override_all_keybindings(self):
        """Should be able to override all keybindings."""
        settings = HotkeySettings(
            next_waiting_ticket="Alt+N",
            back_to_runs="Ctrl+B",
            toggle_theme="Ctrl+Shift+T",
            refresh_dashboard="Ctrl+R",
            open_documentation="Ctrl+D",
            focus_terminal="Ctrl+Shift+T",
        )
        assert settings.next_waiting_ticket == "Alt+N"
        assert settings.back_to_runs == "Ctrl+B"
        assert settings.toggle_theme == "Ctrl+Shift+T"
        assert settings.refresh_dashboard == "Ctrl+R"
        assert settings.open_documentation == "Ctrl+D"
        assert settings.focus_terminal == "Ctrl+Shift+T"

    def test_supports_function_keys(self):
        """Should support F1-F12 function keys."""
        for i in range(1, 13):
            settings = HotkeySettings(next_waiting_ticket=f"F{i}")
            assert settings.next_waiting_ticket == f"F{i}"

    def test_supports_modifier_combinations(self):
        """Should support various modifier key combinations."""
        modifiers = [
            "Ctrl+Shift+N",
            "Ctrl+Alt+N",
            "Shift+Alt+N",
            "Ctrl+Shift+Alt+N",
        ]
        for mod in modifiers:
            settings = HotkeySettings(next_waiting_ticket=mod)
            assert settings.next_waiting_ticket == mod

    def test_supports_special_keys(self):
        """Should support special keys like Escape, Return, etc."""
        special_keys = ["Escape", "Return", "Tab", "Backspace", "Delete"]
        for key in special_keys:
            settings = HotkeySettings(back_to_runs=key)
            assert settings.back_to_runs == key


class TestHotkeySettingsValidation:
    """Test keybinding validation."""

    def test_empty_keybinding_not_allowed(self):
        """Empty keybinding strings should not be allowed."""
        with pytest.raises(ValidationError):
            HotkeySettings(next_waiting_ticket="")

    def test_none_keybinding_not_allowed(self):
        """None keybindings should not be allowed."""
        with pytest.raises((ValidationError, TypeError)):
            HotkeySettings(next_waiting_ticket=None)  # type: ignore

    def test_invalid_key_sequence_rejected(self):
        """Invalid key sequences should be rejected."""
        # Test various invalid formats
        with pytest.raises(ValidationError):
            HotkeySettings(next_waiting_ticket="Ctrl++")  # Double plus

    def test_duplicate_keybindings_allowed_in_model(self):
        """Model should allow duplicate keybindings (validation happens at UI level)."""
        # The model itself doesn't prevent duplicates - that's UI responsibility
        settings = HotkeySettings(
            next_waiting_ticket="Ctrl+N",
            refresh_dashboard="Ctrl+N",  # Duplicate
        )
        assert settings.next_waiting_ticket == "Ctrl+N"
        assert settings.refresh_dashboard == "Ctrl+N"


class TestGUISettingsIntegration:
    """Test HotkeySettings integration with GUISettings."""

    def test_gui_settings_has_hotkeys_field(self):
        """GUISettings should have a hotkeys field."""
        gui = GUISettings()
        assert hasattr(gui, "hotkeys")
        assert isinstance(gui.hotkeys, HotkeySettings)

    def test_gui_settings_uses_hotkey_defaults(self):
        """GUISettings should use HotkeySettings defaults."""
        gui = GUISettings()
        assert gui.hotkeys.next_waiting_ticket == "Ctrl+N"
        assert gui.hotkeys.back_to_runs == "Escape"

    def test_can_override_hotkeys_in_gui_settings(self):
        """Should be able to override hotkeys in GUISettings."""
        gui = GUISettings(
            hotkeys=HotkeySettings(next_waiting_ticket="Alt+N")
        )
        assert gui.hotkeys.next_waiting_ticket == "Alt+N"

    def test_hotkeys_persist_with_theme(self):
        """Hotkeys and theme should coexist in GUISettings."""
        gui = GUISettings(
            theme="dark",
            hotkeys=HotkeySettings(toggle_theme="Ctrl+Shift+T"),
        )
        assert gui.theme == "dark"
        assert gui.hotkeys.toggle_theme == "Ctrl+Shift+T"


class TestLevelUpSettingsIntegration:
    """Test HotkeySettings integration with root LevelUpSettings."""

    def test_levelup_settings_has_gui_hotkeys(self):
        """LevelUpSettings should have GUI hotkeys accessible."""
        settings = LevelUpSettings()
        assert settings.gui.hotkeys.next_waiting_ticket == "Ctrl+N"

    def test_can_set_hotkeys_in_levelup_settings(self):
        """Should be able to set hotkeys through LevelUpSettings."""
        settings = LevelUpSettings(
            gui=GUISettings(
                hotkeys=HotkeySettings(
                    next_waiting_ticket="Ctrl+Shift+N",
                    refresh_dashboard="Ctrl+R",
                )
            )
        )
        assert settings.gui.hotkeys.next_waiting_ticket == "Ctrl+Shift+N"
        assert settings.gui.hotkeys.refresh_dashboard == "Ctrl+R"


class TestHotkeyActionsList:
    """Test comprehensive list of all hotkey actions."""

    def test_all_hotkey_actions_defined(self):
        """All required hotkey actions should be defined in HotkeySettings."""
        settings = HotkeySettings()
        required_actions = [
            "next_waiting_ticket",
            "back_to_runs",
            "toggle_theme",
            "refresh_dashboard",
            "open_documentation",
            "focus_terminal",
        ]
        for action in required_actions:
            assert hasattr(settings, action), f"Missing hotkey action: {action}"
            value = getattr(settings, action)
            assert isinstance(value, str), f"Hotkey {action} should be a string"
            assert len(value) > 0, f"Hotkey {action} should not be empty"


class TestHotkeySettingsSerialization:
    """Test serialization and deserialization of hotkey settings."""

    def test_hotkey_settings_to_dict(self):
        """HotkeySettings should serialize to dict."""
        settings = HotkeySettings()
        data = settings.model_dump()

        assert isinstance(data, dict)
        assert "next_waiting_ticket" in data
        assert data["next_waiting_ticket"] == "Ctrl+N"

    def test_hotkey_settings_from_dict(self):
        """HotkeySettings should deserialize from dict."""
        data = {
            "next_waiting_ticket": "Alt+N",
            "back_to_runs": "Ctrl+B",
            "toggle_theme": "Ctrl+Shift+T",
            "refresh_dashboard": "Ctrl+R",
            "open_documentation": "Ctrl+D",
            "focus_terminal": "Ctrl+Shift+T",
        }
        settings = HotkeySettings(**data)

        assert settings.next_waiting_ticket == "Alt+N"
        assert settings.back_to_runs == "Ctrl+B"

    def test_partial_dict_uses_defaults(self):
        """Partial dict should use defaults for missing fields."""
        data = {"next_waiting_ticket": "Alt+N"}
        settings = HotkeySettings(**data)

        assert settings.next_waiting_ticket == "Alt+N"
        assert settings.back_to_runs == "Escape"  # Default


class TestHotkeyDescriptions:
    """Test that hotkey settings include human-readable descriptions."""

    def test_hotkey_settings_has_action_names(self):
        """HotkeySettings should provide human-readable action names."""
        # This will be implemented as a class method or constant
        settings = HotkeySettings()

        # We should be able to get action descriptions
        # This tests the existence of the metadata structure
        assert hasattr(HotkeySettings, "get_action_description") or \
               hasattr(HotkeySettings, "ACTION_DESCRIPTIONS")

    def test_action_descriptions_cover_all_actions(self):
        """Action descriptions should exist for all hotkey actions."""
        if hasattr(HotkeySettings, "ACTION_DESCRIPTIONS"):
            actions = HotkeySettings.ACTION_DESCRIPTIONS
            assert "next_waiting_ticket" in actions
            assert "back_to_runs" in actions
            assert "toggle_theme" in actions
            assert "refresh_dashboard" in actions
            assert "open_documentation" in actions
            assert "focus_terminal" in actions
