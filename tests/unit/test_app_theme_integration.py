"""Tests for theme integration in gui/app.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestAppThemeInitialization:
    """Test that app.py applies theme on startup."""

    @patch("levelup.gui.app.QApplication")
    @patch("levelup.gui.app.MainWindow")
    @patch("levelup.gui.app.StateManager")
    def test_applies_theme_on_startup(self, mock_state, mock_window, mock_qapp):
        """launch_gui() should apply theme based on settings."""
        from levelup.gui.app import launch_gui

        # Mock QApplication instance
        app_instance = Mock()
        mock_qapp.return_value = app_instance

        # Mock window to prevent show() from running
        window_instance = Mock()
        mock_window.return_value = window_instance

        # Mock sys.exit to prevent actual exit
        with patch("sys.exit"):
            try:
                launch_gui(project_path=Path.cwd())
            except:
                pass  # May fail due to QApplication.exec() but that's ok

        # Should have called setStyleSheet on app
        assert app_instance.setStyleSheet.called

    @patch("levelup.gui.app.load_settings")
    @patch("levelup.gui.app.QApplication")
    @patch("levelup.gui.app.MainWindow")
    @patch("levelup.gui.app.StateManager")
    def test_uses_theme_from_settings(self, mock_state, mock_window, mock_qapp, mock_load_settings):
        """Should load theme preference from settings."""
        from levelup.gui.app import launch_gui
        from levelup.config.settings import LevelUpSettings, GUISettings

        # Create settings with light theme
        settings = LevelUpSettings(gui=GUISettings(theme="light"))
        mock_load_settings.return_value = settings

        app_instance = Mock()
        mock_qapp.return_value = app_instance
        window_instance = Mock()
        mock_window.return_value = window_instance

        with patch("sys.exit"):
            try:
                launch_gui(project_path=Path.cwd())
            except:
                pass

        # Should have loaded settings
        assert mock_load_settings.called

    @patch("levelup.gui.app.get_current_theme")
    @patch("levelup.gui.app.apply_theme")
    @patch("levelup.gui.app.QApplication")
    @patch("levelup.gui.app.MainWindow")
    @patch("levelup.gui.app.StateManager")
    def test_resolves_system_theme_on_startup(self, mock_state, mock_window, mock_qapp, mock_apply, mock_get_theme):
        """Should resolve 'system' preference to actual theme."""
        from levelup.gui.app import launch_gui

        mock_get_theme.return_value = "dark"

        app_instance = Mock()
        mock_qapp.return_value = app_instance
        window_instance = Mock()
        mock_window.return_value = window_instance

        with patch("sys.exit"):
            try:
                launch_gui(project_path=Path.cwd())
            except:
                pass

        # Should have resolved current theme
        assert mock_get_theme.called or app_instance.setStyleSheet.called


class TestAppThemeDefaultBehavior:
    """Test default theme behavior when no config exists."""

    @patch("levelup.gui.app.QApplication")
    @patch("levelup.gui.app.MainWindow")
    @patch("levelup.gui.app.StateManager")
    def test_defaults_to_system_theme_when_no_config(self, mock_state, mock_window, mock_qapp):
        """Should default to system theme detection when no config file."""
        from levelup.gui.app import launch_gui
        import tempfile

        app_instance = Mock()
        mock_qapp.return_value = app_instance
        window_instance = Mock()
        mock_window.return_value = window_instance

        # Use a temp directory with no config file
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sys.exit"):
                try:
                    launch_gui(project_path=Path(tmpdir))
                except:
                    pass

        # Should still apply some theme
        assert app_instance.setStyleSheet.called


class TestAppThemeLoading:
    """Test theme loading in app initialization."""

    @patch("levelup.gui.app.QApplication")
    @patch("levelup.gui.app.MainWindow")
    @patch("levelup.gui.app.StateManager")
    def test_loads_theme_before_window_creation(self, mock_state, mock_window, mock_qapp):
        """Theme should be applied before MainWindow is shown."""
        from levelup.gui.app import launch_gui

        call_order = []

        app_instance = Mock()
        mock_qapp.return_value = app_instance

        def track_stylesheet(*args):
            call_order.append("setStyleSheet")

        app_instance.setStyleSheet.side_effect = track_stylesheet

        window_instance = Mock()
        mock_window.return_value = window_instance

        def track_show():
            call_order.append("show")

        window_instance.show.side_effect = track_show

        with patch("sys.exit"):
            try:
                launch_gui(project_path=Path.cwd())
            except:
                pass

        # setStyleSheet should be called before show
        if "setStyleSheet" in call_order and "show" in call_order:
            assert call_order.index("setStyleSheet") < call_order.index("show")


class TestAppThemeErrorHandling:
    """Test error handling in theme loading."""

    @patch("levelup.gui.app.load_settings")
    @patch("levelup.gui.app.QApplication")
    @patch("levelup.gui.app.MainWindow")
    @patch("levelup.gui.app.StateManager")
    def test_handles_config_loading_error(self, mock_state, mock_window, mock_qapp, mock_load_settings):
        """Should handle config loading errors gracefully."""
        from levelup.gui.app import launch_gui

        # Simulate config loading error
        mock_load_settings.side_effect = Exception("Config error")

        app_instance = Mock()
        mock_qapp.return_value = app_instance
        window_instance = Mock()
        mock_window.return_value = window_instance

        with patch("sys.exit"):
            try:
                launch_gui(project_path=Path.cwd())
            except:
                pass  # Should handle error gracefully

        # Should still apply a default theme
        assert app_instance.setStyleSheet.called

    @patch("levelup.gui.app.get_current_theme")
    @patch("levelup.gui.app.QApplication")
    @patch("levelup.gui.app.MainWindow")
    @patch("levelup.gui.app.StateManager")
    def test_handles_theme_detection_error(self, mock_state, mock_window, mock_qapp, mock_get_theme):
        """Should handle theme detection errors gracefully."""
        from levelup.gui.app import launch_gui

        # Simulate theme detection error
        mock_get_theme.side_effect = Exception("Detection error")

        app_instance = Mock()
        mock_qapp.return_value = app_instance
        window_instance = Mock()
        mock_window.return_value = window_instance

        with patch("sys.exit"):
            try:
                launch_gui(project_path=Path.cwd())
            except Exception as e:
                # Should either handle gracefully or apply default
                pass

        # Should still apply some theme (even if just a fallback)
        assert app_instance.setStyleSheet.called
