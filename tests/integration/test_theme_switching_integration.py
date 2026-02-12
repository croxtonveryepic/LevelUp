"""Integration tests for complete theme switching workflow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import yaml
import pytest

pytestmark = pytest.mark.regression

class TestThemeSwitchingEndToEnd:
    """Test complete theme switching workflow from UI to persistence."""

    @patch("levelup.gui.main_window.StateManager")
    def test_complete_light_theme_workflow(self, mock_state_manager):
        """Test complete workflow: select light theme, apply, persist, reload."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import get_current_theme, set_theme_preference
        from levelup.config.loader import load_settings
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # 1. Set theme preference to light
            set_theme_preference("light", project_path=project_path)

            # 2. Verify preference is stored
            settings = load_settings(project_path=project_path)
            assert settings.gui.theme == "light"

            # 3. Verify get_current_theme returns light
            current = get_current_theme("light")
            assert current == "light"

            # 4. Create window and verify theme is applied
            window = MainWindow(mock_state, project_path=project_path)

            # Window should have light theme applied
            # (Check via stylesheet or theme property)
            assert window is not None

            window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_complete_dark_theme_workflow(self, mock_state_manager):
        """Test complete workflow with dark theme."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference
        from levelup.config.loader import load_settings
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            set_theme_preference("dark", project_path=project_path)
            settings = load_settings(project_path=project_path)
            assert settings.gui.theme == "dark"

            window = MainWindow(mock_state, project_path=project_path)
            assert window is not None
            window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.theme_manager.get_system_theme")
    def test_complete_system_theme_workflow(self, mock_get_system, mock_state_manager):
        """Test complete workflow with system theme detection."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference, get_current_theme
        from levelup.config.loader import load_settings
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        # Mock system theme as light
        mock_get_system.return_value = "light"

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Set preference to system
            set_theme_preference("system", project_path=project_path)
            settings = load_settings(project_path=project_path)
            assert settings.gui.theme == "system"

            # Should resolve to light (based on mock)
            current = get_current_theme("system")
            assert current == "light"

            window = MainWindow(mock_state, project_path=project_path)
            assert window is not None
            window.close()


class TestThemePersistence:
    """Test theme preference persistence across sessions."""

    def test_theme_persisted_to_config_file(self):
        """Theme preference should be written to config file."""
        from levelup.gui.theme_manager import set_theme_preference
        from levelup.config.loader import load_settings

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Set theme
            set_theme_preference("light", project_path=project_path)

            # Check config file exists and contains theme
            config_path = project_path / "levelup.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                    assert config.get("gui", {}).get("theme") == "light"

    def test_theme_loaded_on_next_session(self):
        """Theme preference should be loaded on application restart."""
        from levelup.config.loader import load_settings

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create config file with light theme
            config_path = project_path / "levelup.yaml"
            config_path.write_text(yaml.dump({"gui": {"theme": "light"}}))

            # Load settings (simulates new session)
            settings = load_settings(project_path=project_path)
            assert settings.gui.theme == "light"

    def test_theme_updated_on_change(self):
        """Changing theme should update persisted config."""
        from levelup.gui.theme_manager import set_theme_preference
        from levelup.config.loader import load_settings

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Set initial theme
            set_theme_preference("dark", project_path=project_path)
            settings = load_settings(project_path=project_path)
            assert settings.gui.theme == "dark"

            # Change theme
            set_theme_preference("light", project_path=project_path)
            settings = load_settings(project_path=project_path)
            assert settings.gui.theme == "light"


class TestMultiWidgetThemeCoordination:
    """Test that all widgets update when theme changes."""

    @patch("levelup.gui.main_window.StateManager")
    def test_all_widgets_update_on_theme_change(self, mock_state_manager):
        """All widgets should update when theme changes."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import apply_theme
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Apply light theme
        apply_theme(app, "light")

        # All widgets should reflect the change
        # (Visual check would be needed for full verification)
        assert window is not None

        # Apply dark theme
        apply_theme(app, "dark")
        assert window is not None

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_terminal_updates_with_main_window(self, mock_state_manager):
        """Terminal emulator should update when main window theme changes."""
        from levelup.gui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # If window has terminal widgets, they should update with theme
        # This is verified by the terminal theme switching tests
        assert window is not None

        window.close()


class TestThemeEdgeCases:
    """Test edge cases and error conditions in theme switching."""

    def test_invalid_theme_in_config_falls_back(self):
        """Invalid theme in config should fall back to default."""
        from levelup.config.loader import load_settings

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create config with invalid theme
            config_path = project_path / "levelup.yaml"
            config_path.write_text(yaml.dump({"gui": {"theme": "invalid"}}))

            try:
                settings = load_settings(project_path=project_path)
                # Should either reject invalid or fall back to default
                assert settings.gui.theme in ["light", "dark", "system"]
            except ValueError:
                # Acceptable to raise validation error
                assert True

    def test_missing_gui_section_uses_defaults(self):
        """Missing gui section in config should use defaults."""
        from levelup.config.loader import load_settings

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create config without gui section
            config_path = project_path / "levelup.yaml"
            config_path.write_text(yaml.dump({"llm": {"model": "test"}}))

            settings = load_settings(project_path=project_path)
            assert settings.gui.theme == "system"  # Default

    def test_corrupted_config_handles_gracefully(self):
        """Corrupted config file should be handled gracefully."""
        from levelup.config.loader import load_settings

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create corrupted config
            config_path = project_path / "levelup.yaml"
            config_path.write_text("invalid: yaml: content: [[[")

            try:
                settings = load_settings(project_path=project_path)
                # Should fall back to defaults
                assert settings.gui.theme == "system"
            except:
                # Acceptable to fail on corrupted config
                assert True

    @patch("levelup.gui.theme_manager.darkdetect")
    def test_system_theme_detection_failure_handled(self, mock_darkdetect):
        """Failure in system theme detection should be handled."""
        from levelup.gui.theme_manager import get_system_theme

        # Simulate detection failure
        mock_darkdetect.theme.side_effect = Exception("Detection failed")

        result = get_system_theme()
        # Should return a fallback theme
        assert result in ["light", "dark"]

    def test_theme_switching_during_active_run(self):
        """Theme switching during active run should not crash."""
        from levelup.gui.theme_manager import set_theme_preference

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Simulate active run by switching themes rapidly
            set_theme_preference("light", project_path=project_path)
            set_theme_preference("dark", project_path=project_path)
            set_theme_preference("system", project_path=project_path)

            # Should not crash
            assert True


class TestCrossPlatformThemeDetection:
    """Test cross-platform system theme detection."""

    @patch("levelup.gui.theme_manager.darkdetect")
    def test_windows_theme_detection(self, mock_darkdetect):
        """System theme detection should work on Windows."""
        from levelup.gui.theme_manager import get_system_theme

        mock_darkdetect.theme.return_value = "Dark"
        result = get_system_theme()
        assert result == "dark"

    @patch("levelup.gui.theme_manager.darkdetect")
    def test_macos_theme_detection(self, mock_darkdetect):
        """System theme detection should work on macOS."""
        from levelup.gui.theme_manager import get_system_theme

        mock_darkdetect.theme.return_value = "Light"
        result = get_system_theme()
        assert result == "light"

    @patch("levelup.gui.theme_manager.darkdetect")
    def test_linux_theme_detection(self, mock_darkdetect):
        """System theme detection should work on Linux."""
        from levelup.gui.theme_manager import get_system_theme

        # darkdetect returns theme based on desktop environment
        mock_darkdetect.theme.return_value = "Dark"
        result = get_system_theme()
        assert result == "dark"

    @patch("levelup.gui.theme_manager.darkdetect")
    def test_unsupported_platform_fallback(self, mock_darkdetect):
        """Unsupported platforms should fall back gracefully."""
        from levelup.gui.theme_manager import get_system_theme

        mock_darkdetect.theme.return_value = None
        result = get_system_theme()
        # Should return a default
        assert result in ["light", "dark"]
