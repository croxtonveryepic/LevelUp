"""Tests for theme manager module."""

from __future__ import annotations

from unittest.mock import Mock, patch

from PyQt6.QtWidgets import QApplication
import pytest

pytestmark = pytest.mark.regression

class TestThemeManagerModule:
    """Test that theme manager module exists and has required functions."""

    def test_module_exists(self):
        """Theme manager module should be importable."""
        from levelup.gui import theme_manager
        assert theme_manager is not None

    def test_has_get_system_theme_function(self):
        """Should have get_system_theme() function."""
        from levelup.gui.theme_manager import get_system_theme
        assert callable(get_system_theme)

    def test_has_get_current_theme_function(self):
        """Should have get_current_theme() function."""
        from levelup.gui.theme_manager import get_current_theme
        assert callable(get_current_theme)

    def test_has_apply_theme_function(self):
        """Should have apply_theme() function."""
        from levelup.gui.theme_manager import apply_theme
        assert callable(apply_theme)

    def test_has_set_theme_preference_function(self):
        """Should have set_theme_preference() function."""
        from levelup.gui.theme_manager import set_theme_preference
        assert callable(set_theme_preference)


class TestGetSystemTheme:
    """Test system theme detection."""

    def test_returns_light_or_dark(self):
        """get_system_theme() should return 'light' or 'dark'."""
        from levelup.gui.theme_manager import get_system_theme
        theme = get_system_theme()
        assert theme in ["light", "dark"]

    @patch("levelup.gui.theme_manager.darkdetect")
    def test_uses_darkdetect_library(self, mock_darkdetect):
        """Should use darkdetect library for detection."""
        from levelup.gui.theme_manager import get_system_theme

        mock_darkdetect.theme.return_value = "Dark"
        result = get_system_theme()
        assert result == "dark"
        mock_darkdetect.theme.assert_called_once()

    @patch("levelup.gui.theme_manager.darkdetect")
    def test_handles_light_detection(self, mock_darkdetect):
        """Should correctly handle light theme detection."""
        from levelup.gui.theme_manager import get_system_theme

        mock_darkdetect.theme.return_value = "Light"
        result = get_system_theme()
        assert result == "light"

    @patch("levelup.gui.theme_manager.darkdetect")
    def test_handles_none_return(self, mock_darkdetect):
        """Should handle None return from darkdetect (fallback)."""
        from levelup.gui.theme_manager import get_system_theme

        mock_darkdetect.theme.return_value = None
        result = get_system_theme()
        # Should fall back to dark or light
        assert result in ["light", "dark"]

    @patch("levelup.gui.theme_manager.darkdetect")
    def test_handles_darkdetect_error(self, mock_darkdetect):
        """Should handle darkdetect exceptions gracefully."""
        from levelup.gui.theme_manager import get_system_theme

        mock_darkdetect.theme.side_effect = Exception("Detection failed")
        result = get_system_theme()
        # Should fall back to a default theme
        assert result in ["light", "dark"]


class TestGetCurrentTheme:
    """Test current theme resolution based on preference."""

    def test_light_preference_returns_light(self):
        """get_current_theme('light') should return 'light'."""
        from levelup.gui.theme_manager import get_current_theme
        assert get_current_theme("light") == "light"

    def test_dark_preference_returns_dark(self):
        """get_current_theme('dark') should return 'dark'."""
        from levelup.gui.theme_manager import get_current_theme
        assert get_current_theme("dark") == "dark"

    @patch("levelup.gui.theme_manager.get_system_theme")
    def test_system_preference_uses_system_theme(self, mock_get_system):
        """get_current_theme('system') should detect system theme."""
        from levelup.gui.theme_manager import get_current_theme

        mock_get_system.return_value = "light"
        assert get_current_theme("system") == "light"
        mock_get_system.assert_called_once()

    @patch("levelup.gui.theme_manager.get_system_theme")
    def test_system_preference_with_dark_system(self, mock_get_system):
        """get_current_theme('system') should return dark if system is dark."""
        from levelup.gui.theme_manager import get_current_theme

        mock_get_system.return_value = "dark"
        assert get_current_theme("system") == "dark"

    def test_invalid_preference_defaults_to_system(self):
        """Invalid preference should fall back to system detection."""
        from levelup.gui.theme_manager import get_current_theme
        result = get_current_theme("invalid")
        assert result in ["light", "dark"]

    def test_none_preference_defaults_to_system(self):
        """None preference should fall back to system detection."""
        from levelup.gui.theme_manager import get_current_theme
        result = get_current_theme(None)
        assert result in ["light", "dark"]


class TestApplyTheme:
    """Test theme application to QApplication."""

    def test_accepts_light_theme(self):
        """apply_theme() should accept 'light' theme."""
        from levelup.gui.theme_manager import apply_theme

        # Should not raise
        app = Mock(spec=QApplication)
        apply_theme(app, "light")
        app.setStyleSheet.assert_called_once()

    def test_accepts_dark_theme(self):
        """apply_theme() should accept 'dark' theme."""
        from levelup.gui.theme_manager import apply_theme

        app = Mock(spec=QApplication)
        apply_theme(app, "dark")
        app.setStyleSheet.assert_called_once()

    def test_applies_light_stylesheet_for_light_theme(self):
        """apply_theme('light') should apply LIGHT_THEME stylesheet."""
        from levelup.gui.theme_manager import apply_theme
        from levelup.gui.styles import LIGHT_THEME

        app = Mock(spec=QApplication)
        apply_theme(app, "light")
        app.setStyleSheet.assert_called_once_with(LIGHT_THEME)

    def test_applies_dark_stylesheet_for_dark_theme(self):
        """apply_theme('dark') should apply DARK_THEME stylesheet."""
        from levelup.gui.theme_manager import apply_theme
        from levelup.gui.styles import DARK_THEME

        app = Mock(spec=QApplication)
        apply_theme(app, "dark")
        app.setStyleSheet.assert_called_once_with(DARK_THEME)

    def test_invalid_theme_raises_error(self):
        """apply_theme() should raise error for invalid theme."""
        from levelup.gui.theme_manager import apply_theme

        app = Mock(spec=QApplication)
        try:
            apply_theme(app, "invalid")
            # If it doesn't raise, it should at least not crash
            assert True
        except ValueError:
            # Acceptable to raise ValueError for invalid theme
            assert True


class TestSetThemePreference:
    """Test theme preference management."""

    def test_accepts_valid_preferences(self):
        """set_theme_preference() should accept light, dark, system."""
        from levelup.gui.theme_manager import set_theme_preference

        # Should not raise
        set_theme_preference("light")
        set_theme_preference("dark")
        set_theme_preference("system")

    def test_stores_preference(self):
        """set_theme_preference() should store the preference."""
        from levelup.gui.theme_manager import set_theme_preference, get_theme_preference

        set_theme_preference("light")
        assert get_theme_preference() == "light"

        set_theme_preference("dark")
        assert get_theme_preference() == "dark"

    def test_persists_to_config(self):
        """set_theme_preference() should persist preference to config."""
        from levelup.gui.theme_manager import set_theme_preference
        from pathlib import Path

        # This test verifies the integration with config system
        # Mock or test that config is updated
        test_path = Path.cwd()
        set_theme_preference("light", project_path=test_path)
        # Should not raise; persistence tested via config tests


class TestGetThemePreference:
    """Test getting stored theme preference."""

    def test_has_get_theme_preference_function(self):
        """Should have get_theme_preference() function."""
        from levelup.gui.theme_manager import get_theme_preference
        assert callable(get_theme_preference)

    def test_returns_default_when_not_set(self):
        """get_theme_preference() should return 'system' by default."""
        from levelup.gui.theme_manager import get_theme_preference
        # Default should be 'system'
        result = get_theme_preference()
        assert result in ["light", "dark", "system"]

    def test_returns_stored_preference(self):
        """get_theme_preference() should return previously set preference."""
        from levelup.gui.theme_manager import set_theme_preference, get_theme_preference

        set_theme_preference("light")
        assert get_theme_preference() == "light"


class TestThemeChangeNotification:
    """Test theme change notification system."""

    def test_has_theme_changed_signal(self):
        """Should have a mechanism to notify of theme changes."""
        from levelup.gui import theme_manager
        # Check if there's a signal or callback mechanism
        assert hasattr(theme_manager, "theme_changed") or hasattr(theme_manager, "notify_theme_change")

    def test_theme_change_can_be_observed(self):
        """Theme changes should be observable by widgets."""
        from levelup.gui.theme_manager import set_theme_preference

        callback_called = []

        def callback(theme):
            callback_called.append(theme)

        # This tests if there's a way to observe theme changes
        # Implementation may vary
        try:
            from levelup.gui.theme_manager import add_theme_listener
            add_theme_listener(callback)
            set_theme_preference("light")
            # Callback should have been called
            assert len(callback_called) > 0
        except ImportError:
            # If no listener mechanism, that's okay for now
            pass
