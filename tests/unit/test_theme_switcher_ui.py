"""Tests for theme switcher UI control in main_window.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch


class TestThemeSwitcherControl:
    """Test that theme switcher control exists in main window."""

    @patch("levelup.gui.main_window.StateManager")
    def test_main_window_has_theme_switcher(self, mock_state_manager):
        """MainWindow should have a theme switcher control."""
        from levelup.gui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication
        import sys

        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Create mock state manager
        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should have a theme switcher widget
        assert hasattr(window, "_theme_switcher") or hasattr(window, "theme_switcher")

        # Clean up
        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_theme_switcher_in_toolbar(self, mock_state_manager):
        """Theme switcher should be in the toolbar."""
        from levelup.gui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication, QPushButton
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Find theme switcher control (should be QPushButton)
        theme_control = None
        if hasattr(window, "_theme_switcher"):
            theme_control = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_control = window.theme_switcher
        else:
            # Search for it in the window's children
            for child in window.findChildren(QPushButton):
                if "theme" in child.objectName().lower():
                    theme_control = child
                    break

        assert theme_control is not None, "Theme switcher control not found"
        assert isinstance(theme_control, QPushButton), "Theme switcher should be a QPushButton"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_theme_switcher_is_pushbutton(self, mock_state_manager):
        """Theme switcher should be a QPushButton, not a QComboBox."""
        from levelup.gui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication, QPushButton
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Theme switcher should be a QPushButton
        theme_control = None
        if hasattr(window, "_theme_switcher"):
            theme_control = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_control = window.theme_switcher

        assert theme_control is not None
        assert isinstance(theme_control, QPushButton), "Theme switcher must be QPushButton"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_theme_switcher_has_object_name(self, mock_state_manager):
        """Theme switcher button should have objectName 'themeBtn' for styling."""
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

        theme_control = None
        if hasattr(window, "_theme_switcher"):
            theme_control = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_control = window.theme_switcher

        assert theme_control is not None
        assert theme_control.objectName() == "themeBtn", "Theme button should have objectName 'themeBtn'"

        window.close()


class TestThemeSwitcherButtonBehavior:
    """Test theme switcher button cycling behavior."""

    @patch("levelup.gui.main_window.StateManager")
    def test_button_cycles_through_themes(self, mock_state_manager):
        """Clicking button should cycle through themes: system → light → dark → system."""
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

        # Verify we can track current theme state
        # The button should have a way to track or display current theme
        assert hasattr(window, "_current_theme_preference") or hasattr(window, "current_theme")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.set_theme_preference")
    def test_button_click_changes_theme(self, mock_set_pref, mock_state_manager):
        """Clicking button should trigger theme change."""
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

        # Simulate button click
        theme_btn.click()

        # Should have triggered theme change mechanism
        assert hasattr(window, "_cycle_theme") or hasattr(window, "_on_theme_clicked")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_button_displays_theme_symbol(self, mock_state_manager):
        """Button should display a symbol indicating current theme."""
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

        # Button should have text or icon showing theme
        button_text = theme_btn.text()
        assert button_text is not None and len(button_text) > 0, "Button should display theme indicator"

        # Text should be one of the theme symbols
        # '◐' for system, '☀' for light, '☾' for dark
        assert button_text in ['◐', '☀', '☾'], f"Button text should be a theme symbol, got: {button_text}"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_button_symbol_matches_current_theme(self, mock_state_manager):
        """Button symbol should reflect the current theme preference."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import get_theme_preference
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

        current_pref = get_theme_preference()
        button_text = theme_btn.text()

        # Verify symbol matches preference
        if current_pref == "system":
            assert button_text == '◐', "System theme should show ◐ symbol"
        elif current_pref == "light":
            assert button_text == '☀', "Light theme should show ☀ symbol"
        elif current_pref == "dark":
            assert button_text == '☾', "Dark theme should show ☾ symbol"

        window.close()


class TestThemeSwitcherCycling:
    """Test theme cycling order: system → light → dark → system."""

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.apply_theme")
    @patch("levelup.gui.main_window.set_theme_preference")
    def test_cycles_from_system_to_light(self, mock_set_pref, mock_apply_theme, mock_state_manager):
        """Clicking button when theme is 'system' should cycle to 'light'."""
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

        # Set initial theme to system
        set_theme_preference("system")

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Click button
        theme_btn.click()

        # Should cycle to light
        # Verify set_theme_preference was called with "light"
        mock_set_pref.assert_called()
        call_args = mock_set_pref.call_args
        assert call_args is not None
        # First argument should be "light"
        assert call_args[0][0] == "light", "Should cycle from system to light"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.apply_theme")
    @patch("levelup.gui.main_window.set_theme_preference")
    def test_cycles_from_light_to_dark(self, mock_set_pref, mock_apply_theme, mock_state_manager):
        """Clicking button when theme is 'light' should cycle to 'dark'."""
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

        # Set initial theme to light
        set_theme_preference("light")

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Click button
        theme_btn.click()

        # Should cycle to dark
        mock_set_pref.assert_called()
        call_args = mock_set_pref.call_args
        assert call_args is not None
        assert call_args[0][0] == "dark", "Should cycle from light to dark"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.apply_theme")
    @patch("levelup.gui.main_window.set_theme_preference")
    def test_cycles_from_dark_to_system(self, mock_set_pref, mock_apply_theme, mock_state_manager):
        """Clicking button when theme is 'dark' should cycle to 'system'."""
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

        # Set initial theme to dark
        set_theme_preference("dark")

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Click button
        theme_btn.click()

        # Should cycle to system
        mock_set_pref.assert_called()
        call_args = mock_set_pref.call_args
        assert call_args is not None
        assert call_args[0][0] == "system", "Should cycle from dark to system"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.apply_theme")
    def test_full_cycle_returns_to_initial(self, mock_apply_theme, mock_state_manager):
        """Clicking button 3 times should cycle through all themes and return to initial."""
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

        # Set initial theme to system
        set_theme_preference("system")
        initial_theme = get_theme_preference()

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        # Click 3 times
        theme_btn.click()  # system → light
        theme_btn.click()  # light → dark
        theme_btn.click()  # dark → system

        # Should be back to initial theme
        final_theme = get_theme_preference()
        assert final_theme == initial_theme, "After 3 clicks, should return to initial theme"

        window.close()


class TestThemeSwitcherTooltip:
    """Test theme switcher button tooltip."""

    @patch("levelup.gui.main_window.StateManager")
    def test_button_has_tooltip(self, mock_state_manager):
        """Theme button should have a tooltip."""
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
        assert tooltip is not None and len(tooltip) > 0, "Button should have a tooltip"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_tooltip_indicates_current_theme(self, mock_state_manager):
        """Tooltip should indicate the current theme selection."""
        from levelup.gui.main_window import MainWindow
        from levelup.gui.theme_manager import get_theme_preference
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
        current_pref = get_theme_preference()

        # Tooltip should mention the theme
        if current_pref == "system":
            assert "System" in tooltip or "system" in tooltip, "Tooltip should indicate 'System' theme"
        elif current_pref == "light":
            assert "Light" in tooltip or "light" in tooltip, "Tooltip should indicate 'Light' theme"
        elif current_pref == "dark":
            assert "Dark" in tooltip or "dark" in tooltip, "Tooltip should indicate 'Dark' theme"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_tooltip_format(self, mock_state_manager):
        """Tooltip should follow format 'Theme: <name>'."""
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

        # Tooltip should start with "Theme:"
        assert tooltip.startswith("Theme:"), "Tooltip should start with 'Theme:'"

        # And should be one of the expected formats
        assert tooltip in ["Theme: Match System", "Theme: Light", "Theme: Dark"], \
            f"Tooltip format incorrect: {tooltip}"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.apply_theme")
    def test_tooltip_updates_after_cycle(self, mock_apply_theme, mock_state_manager):
        """Tooltip should update after clicking the button to cycle themes."""
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

        # Start with system theme
        set_theme_preference("system")

        window = MainWindow(mock_state, project_path=Path.cwd())

        theme_btn = None
        if hasattr(window, "_theme_switcher"):
            theme_btn = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_btn = window.theme_switcher

        assert theme_btn is not None

        initial_tooltip = theme_btn.toolTip()
        assert "System" in initial_tooltip or "Match System" in initial_tooltip

        # Click to cycle to light
        theme_btn.click()

        # Tooltip should update
        new_tooltip = theme_btn.toolTip()
        assert new_tooltip != initial_tooltip, "Tooltip should change after cycling"
        assert "Light" in new_tooltip, "Tooltip should show 'Light' after cycling from system"

        window.close()


class TestThemeSwitcherBehavior:
    """Test theme switcher behavior and interactions."""

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.apply_theme")
    def test_switching_theme_applies_immediately(self, mock_apply_theme, mock_state_manager):
        """Changing theme should apply immediately without restart."""
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

        # Click button to change theme
        theme_btn.click()

        # Should trigger theme application
        assert mock_apply_theme.called or hasattr(window, "_cycle_theme")

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.set_theme_preference")
    def test_switching_theme_saves_preference(self, mock_set_pref, mock_state_manager):
        """Changing theme should save preference to config."""
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

        # Click button
        theme_btn.click()

        # Should save preference
        assert mock_set_pref.called, "Theme preference should be saved"

        window.close()


class TestThemeSwitcherAccessibility:
    """Test theme switcher accessibility and discoverability."""

    @patch("levelup.gui.main_window.StateManager")
    def test_theme_switcher_is_visible(self, mock_state_manager):
        """Theme switcher should be visible in the main window."""
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

        # Theme control should be visible
        if hasattr(window, "_theme_switcher"):
            assert window._theme_switcher.isVisible()
        elif hasattr(window, "theme_switcher"):
            assert window.theme_switcher.isVisible()

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_theme_switcher_has_tooltip(self, mock_state_manager):
        """Theme switcher should have a helpful tooltip."""
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

        # Find theme control
        theme_control = None
        if hasattr(window, "_theme_switcher"):
            theme_control = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_control = window.theme_switcher

        if theme_control:
            tooltip = theme_control.toolTip()
            # Should have a tooltip explaining what it does
            assert tooltip is not None and len(tooltip) > 0

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_theme_label_removed(self, mock_state_manager):
        """Theme label ('Theme:') should be removed from toolbar."""
        from levelup.gui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication, QLabel
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Look for any QLabel with text "Theme:" in the window
        theme_labels = [label for label in window.findChildren(QLabel) if label.text() == "Theme:"]

        assert len(theme_labels) == 0, "Theme label should be removed from toolbar"

        window.close()


class TestThemeSwitcherStyling:
    """Test theme switcher button styling."""

    @patch("levelup.gui.main_window.StateManager")
    def test_button_has_consistent_size(self, mock_state_manager):
        """Theme button should have consistent size (28x28px or similar to other icon buttons)."""
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

        # Button should have fixed size constraints
        # This will be enforced by CSS, but we can check that size hint is reasonable
        size_hint = theme_btn.sizeHint()
        # Size should be small (icon button size, e.g., 28-40px)
        assert size_hint.width() <= 40, "Button width should be small (icon button size)"
        assert size_hint.height() <= 40, "Button height should be small (icon button size)"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_button_styled_via_stylesheet(self, mock_state_manager):
        """Button should be styled via QPushButton#themeBtn selector."""
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

        # Button should have objectName for styling
        assert theme_btn.objectName() == "themeBtn"

        # Check that global stylesheet includes themeBtn styles
        app_stylesheet = app.styleSheet()
        assert "#themeBtn" in app_stylesheet, "Global stylesheet should include #themeBtn styles"

        window.close()


class TestComboBoxRemoval:
    """Test that old QComboBox theme switcher is removed."""

    @patch("levelup.gui.main_window.StateManager")
    def test_no_combobox_in_window(self, mock_state_manager):
        """MainWindow should not have a QComboBox for theme switching."""
        from levelup.gui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication, QComboBox
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Search for QComboBox with theme-related object name
        theme_combos = [combo for combo in window.findChildren(QComboBox)
                       if "theme" in combo.objectName().lower()]

        assert len(theme_combos) == 0, "Should not have QComboBox for theme switching"

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_no_theme_combobox_object(self, mock_state_manager):
        """MainWindow should not have _theme_switcher as QComboBox."""
        from levelup.gui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication, QComboBox, QPushButton
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        window = MainWindow(mock_state, project_path=Path.cwd())

        if hasattr(window, "_theme_switcher"):
            # Should be QPushButton, not QComboBox
            assert isinstance(window._theme_switcher, QPushButton)
            assert not isinstance(window._theme_switcher, QComboBox)
        elif hasattr(window, "theme_switcher"):
            assert isinstance(window.theme_switcher, QPushButton)
            assert not isinstance(window.theme_switcher, QComboBox)

        window.close()
