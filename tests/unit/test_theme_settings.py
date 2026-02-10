"""Tests for GUI theme settings in config/settings.py."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from levelup.config.loader import load_settings
from levelup.config.settings import GUISettings, LevelUpSettings


class TestGUISettings:
    """Test GUISettings model."""

    def test_defaults(self):
        """GUISettings should default to system theme."""
        settings = GUISettings()
        assert settings.theme == "system"

    def test_valid_theme_values(self):
        """GUISettings should accept light, dark, and system themes."""
        light = GUISettings(theme="light")
        assert light.theme == "light"

        dark = GUISettings(theme="dark")
        assert dark.theme == "dark"

        system = GUISettings(theme="system")
        assert system.theme == "system"

    def test_invalid_theme_raises_validation_error(self):
        """GUISettings should reject invalid theme values."""
        with pytest.raises(ValueError):
            GUISettings(theme="invalid")

    def test_serialization_roundtrip(self):
        """GUISettings should serialize and deserialize correctly."""
        settings = GUISettings(theme="light")
        data = settings.model_dump()
        restored = GUISettings(**data)
        assert restored == settings
        assert restored.theme == "light"

    def test_json_roundtrip(self):
        """GUISettings should handle JSON serialization."""
        settings = GUISettings(theme="dark")
        json_str = settings.model_dump_json()
        restored = GUISettings.model_validate_json(json_str)
        assert restored == settings
        assert restored.theme == "dark"


class TestLevelUpSettingsWithGUI:
    """Test LevelUpSettings integration with GUISettings."""

    def test_gui_settings_included_in_root(self):
        """LevelUpSettings should have a gui field."""
        settings = LevelUpSettings()
        assert hasattr(settings, "gui")
        assert isinstance(settings.gui, GUISettings)

    def test_gui_defaults_to_system_theme(self):
        """Root settings should have system theme by default."""
        settings = LevelUpSettings()
        assert settings.gui.theme == "system"

    def test_nested_gui_settings_override(self):
        """Should be able to override gui theme in root settings."""
        settings = LevelUpSettings(gui=GUISettings(theme="light"))
        assert settings.gui.theme == "light"


class TestGUISettingsConfigLoading:
    """Test loading GUI settings from config files."""

    def test_gui_theme_loaded_from_file(self, tmp_path: Path):
        """Config file should be able to set gui.theme."""
        config = tmp_path / "levelup.yaml"
        config.write_text(yaml.dump({"gui": {"theme": "light"}}))
        settings = load_settings(project_path=tmp_path)
        assert settings.gui.theme == "light"

    def test_gui_theme_defaults_when_not_in_file(self, tmp_path: Path):
        """When gui.theme not in config, should use default (system)."""
        config = tmp_path / "levelup.yaml"
        config.write_text(yaml.dump({"llm": {"model": "test"}}))
        settings = load_settings(project_path=tmp_path)
        assert settings.gui.theme == "system"

    def test_gui_theme_override_takes_precedence(self, tmp_path: Path):
        """Overrides should take precedence over config file."""
        config = tmp_path / "levelup.yaml"
        config.write_text(yaml.dump({"gui": {"theme": "light"}}))
        settings = load_settings(
            project_path=tmp_path,
            overrides={"gui": {"theme": "dark"}},
        )
        assert settings.gui.theme == "dark"

    def test_partial_gui_settings_preserve_defaults(self, tmp_path: Path):
        """Partial overrides should preserve defaults."""
        config = tmp_path / "levelup.yaml"
        config.write_text(yaml.dump({"gui": {"theme": "dark"}}))
        settings = load_settings(project_path=tmp_path)
        assert settings.gui.theme == "dark"

    def test_empty_gui_section_uses_defaults(self, tmp_path: Path):
        """Empty gui section should use default theme."""
        config = tmp_path / "levelup.yaml"
        config.write_text(yaml.dump({"gui": {}}))
        settings = load_settings(project_path=tmp_path)
        assert settings.gui.theme == "system"

    def test_gui_theme_persists_in_serialization(self, tmp_path: Path):
        """GUI theme should persist when settings are saved."""
        config = tmp_path / "levelup.yaml"
        config.write_text(yaml.dump({"gui": {"theme": "light"}}))
        settings = load_settings(project_path=tmp_path)

        # Serialize and restore
        data = settings.model_dump()
        restored = LevelUpSettings(**data)
        assert restored.gui.theme == "light"
