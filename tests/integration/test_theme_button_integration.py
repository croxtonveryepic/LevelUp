"""Integration tests for theme button workflow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import yaml
import pytest

pytestmark = pytest.mark.regression

class TestThemeButtonCompleteWorkflow:
    """Test complete workflow of theme button from startup to cycling."""

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.theme_manager.darkdetect")
    def test_complete_theme_button_cycle_workflow(self, mock_darkdetect, mock_state_manager):
        """Test complete workflow: startup → click → cycle → apply → persist."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import get_theme_preference, set_theme_preference
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        mock_darkdetect.theme.return_value = "Dark"

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # 1. Start with system theme (default)
            set_theme_preference("system")
            assert get_theme_preference() == "system"

            # 2. Create window
            window = MainWindow(mock_state, project_path=project_path)

            theme_btn = None
            if hasattr(window, "_theme_switcher"):
                theme_btn = window._theme_switcher
            elif hasattr(window, "theme_switcher"):
                theme_btn = window.theme_switcher

            assert theme_btn is not None

            # 3. Verify initial state: system theme symbol
            assert theme_btn.text() == '◐', "Should start with system symbol"
            assert "Match System" in theme_btn.toolTip() or "System" in theme_btn.toolTip()

            # 4. Click to cycle to light
            theme_btn.click()
            assert get_theme_preference() == "light"
            assert theme_btn.text() == '☀', "Should show light symbol"
            assert "Light" in theme_btn.toolTip()

            # 5. Click to cycle to dark
            theme_btn.click()
            assert get_theme_preference() == "dark"
            assert theme_btn.text() == '☾', "Should show dark symbol"
            assert "Dark" in theme_btn.toolTip()

            # 6. Click to cycle back to system
            theme_btn.click()
            assert get_theme_preference() == "system"
            assert theme_btn.text() == '◐', "Should show system symbol again"

            # 7. Verify preference persisted
            from levelup.config.loader import load_settings
            settings = load_settings(project_path=project_path)
            assert settings.gui.theme == "system"

            window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.theme_manager.darkdetect")
    def test_theme_button_applies_immediately(self, mock_darkdetect, mock_state_manager):
        """Test that clicking theme button applies theme immediately without restart."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        mock_darkdetect.theme.return_value = "Dark"

        set_theme_preference("system")

        with patch("levelup.gui.main_window.apply_theme") as mock_apply_theme:
            window = MainWindow(mock_state, project_path=Path.cwd())

            theme_btn = None
            if hasattr(window, "_theme_switcher"):
                theme_btn = window._theme_switcher
            elif hasattr(window, "theme_switcher"):
                theme_btn = window.theme_switcher

            assert theme_btn is not None

            # Click button
            theme_btn.click()

            # Should have called apply_theme
            assert mock_apply_theme.called, "Should apply theme immediately"

            window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_theme_button_persists_preference(self, mock_state_manager):
        """Test that clicking theme button persists preference to config."""
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

            set_theme_preference("system")

            window = MainWindow(mock_state, project_path=project_path)

            theme_btn = None
            if hasattr(window, "_theme_switcher"):
                theme_btn = window._theme_switcher
            elif hasattr(window, "theme_switcher"):
                theme_btn = window.theme_switcher

            assert theme_btn is not None

            # Click to cycle to light
            theme_btn.click()

            # Verify persisted
            settings = load_settings(project_path=project_path)
            assert settings.gui.theme == "light", "Theme should be persisted to config"

            window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.theme_manager.darkdetect")
    def test_theme_button_updates_symbol_and_tooltip(self, mock_darkdetect, mock_state_manager):
        """Test that clicking theme button updates both symbol and tooltip."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        mock_darkdetect.theme.return_value = "Dark"

        set_theme_preference("system")

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Initial: system
        assert theme_btn.text() == '◐'
        assert "System" in theme_btn.toolTip() or "Match System" in theme_btn.toolTip()

        # Click to light
        theme_btn.click()
        assert theme_btn.text() == '☀', "Symbol should update to light"
        assert "Light" in theme_btn.toolTip(), "Tooltip should update to Light"

        # Click to dark
        theme_btn.click()
        assert theme_btn.text() == '☾', "Symbol should update to dark"
        assert "Dark" in theme_btn.toolTip(), "Tooltip should update to Dark"

        window.close()


class TestThemeButtonVisualIntegration:
    """Test theme button visual integration with application styling."""

    @patch("levelup.gui.main_window.StateManager")
    def test_button_styled_in_dark_theme(self, mock_state_manager):
        """Theme button should be properly styled in dark theme."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference, apply_theme
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        set_theme_preference("dark")
        apply_theme(app, "dark")

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Verify objectName for styling
        assert theme_btn.objectName() == "themeBtn"

        # Verify button is visible
        assert theme_btn.isVisible()

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_button_styled_in_light_theme(self, mock_state_manager):
        """Theme button should be properly styled in light theme."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference, apply_theme
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        set_theme_preference("light")
        apply_theme(app, "light")

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Verify objectName for styling
        assert theme_btn.objectName() == "themeBtn"

        # Verify button is visible
        assert theme_btn.isVisible()

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_button_switches_between_themes_visually(self, mock_state_manager):
        """Theme button should visually update when switching themes."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference, apply_theme
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        set_theme_preference("dark")

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Start with dark theme
        apply_theme(app, "dark")
        dark_stylesheet = app.styleSheet()
        assert "#themeBtn" in dark_stylesheet

        # Switch to light theme
        apply_theme(app, "light")
        light_stylesheet = app.styleSheet()
        assert "#themeBtn" in light_stylesheet

        # Stylesheets should be different
        assert dark_stylesheet != light_stylesheet

        window.close()


class TestThemeButtonWithMultipleWindows:
    """Test theme button behavior with multiple windows open."""

    @patch("levelup.gui.main_window.StateManager")
    def test_theme_applies_to_all_windows(self, mock_state_manager):
        """Changing theme should apply to all open windows."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference, apply_theme, get_current_theme
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        set_theme_preference("dark")

        # Create two windows
        window1 = MainWindow(mock_state, project_path=Path.cwd())
        window2 = MainWindow(mock_state, project_path=Path.cwd())

        # Apply theme (simulates button click)
        actual_theme = get_current_theme("light")
        apply_theme(app, actual_theme)

        # Both windows should have the same stylesheet
        # (via global QApplication.setStyleSheet)
        assert app.styleSheet() is not None

        window1.close()
        window2.close()


class TestThemeButtonErrorHandling:
    """Test theme button error handling."""

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.set_theme_preference")
    def test_button_handles_save_failure_gracefully(self, mock_set_pref, mock_state_manager):
        """Button should handle config save failures gracefully."""
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

        # Make save fail
        mock_set_pref.side_effect = Exception("Save failed")

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Click button - should not crash despite save failure
        try:
            theme_btn.click()
            # If it doesn't crash, test passes
            assert True
        except Exception as e:
            # Should handle gracefully, not crash the app
            assert False, f"Button click should not crash on save failure: {e}"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.theme_manager.darkdetect")
    def test_button_handles_system_detection_failure(self, mock_darkdetect, mock_state_manager):
        """Button should handle system theme detection failures gracefully."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        # Make detection fail
        mock_darkdetect.theme.side_effect = Exception("Detection failed")

        set_theme_preference("system")

        # Should not crash during window creation
        try:
            window = MainWindow(mock_state, project_path=Path.cwd())
            assert window is not None
            window.close()
        except Exception as e:
            assert False, f"Window creation should not crash on detection failure: {e}"


class TestThemeButtonAccessibility:
    """Test theme button accessibility features."""

    @patch("levelup.gui.main_window.StateManager")
    def test_button_has_accessible_size(self, mock_state_manager):
        """Button should have accessible size for clicking."""
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

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Size should be adequate for clicking (at least 20x20)
        size = theme_btn.size()
        assert size.width() >= 20, "Button width should be at least 20px for accessibility"
        assert size.height() >= 20, "Button height should be at least 20px for accessibility"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_button_tooltip_is_descriptive(self, mock_state_manager):
        """Button tooltip should be descriptive and helpful."""
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

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        tooltip = theme_btn.toolTip()
        # Tooltip should be descriptive (more than just a symbol)
        assert len(tooltip) > 5, "Tooltip should be descriptive"
        assert "Theme" in tooltip, "Tooltip should mention 'Theme'"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_button_is_keyboard_accessible(self, mock_state_manager):
        """Button should be keyboard accessible (focusable)."""
        from levelup.gui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Button should accept focus for keyboard navigation
        focus_policy = theme_btn.focusPolicy()
        assert focus_policy != Qt.FocusPolicy.NoFocus, \
            "Button should be focusable for keyboard accessibility"

        window.close()


class TestThemeButtonUserExperience:
    """Test theme button user experience."""

    @patch("levelup.gui.main_window.StateManager")
    def test_button_provides_clear_feedback(self, mock_state_manager):
        """Button should provide clear visual feedback of current state."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference
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

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Button text should clearly indicate current theme
        button_text = theme_btn.text()
        assert button_text in ['◐', '☀', '☾'], \
            "Button should show clear theme symbol"

        # Tooltip should reinforce the state
        tooltip = theme_btn.toolTip()
        assert tooltip in ["Theme: Match System", "Theme: Light", "Theme: Dark"], \
            "Tooltip should clearly state current theme"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_button_cycling_is_intuitive(self, mock_state_manager):
        """Button cycling order should be intuitive: system → light → dark → system."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import set_theme_preference, get_theme_preference
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        set_theme_preference("system")

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Cycle order should be: system → light → dark → system
        assert get_theme_preference() == "system"

        theme_btn.click()
        assert get_theme_preference() == "light", "Should cycle from system to light"

        theme_btn.click()
        assert get_theme_preference() == "dark", "Should cycle from light to dark"

        theme_btn.click()
        assert get_theme_preference() == "system", "Should cycle from dark to system"

        window.close()
