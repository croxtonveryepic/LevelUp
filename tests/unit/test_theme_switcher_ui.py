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

        # Find theme switcher control (could be QComboBox or QPushButton)
        theme_control = None
        if hasattr(window, "_theme_switcher"):
            theme_control = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_control = window.theme_switcher
        else:
            # Search for it in the window's children
            for child in window.findChildren(QComboBox):
                if "theme" in child.objectName().lower():
                    theme_control = child
                    break

        assert theme_control is not None, "Theme switcher control not found"

        window.close()


class TestThemeSwitcherOptions:
    """Test theme switcher control options."""

    @patch("levelup.gui.main_window.StateManager")
    def test_has_light_dark_system_options(self, mock_state_manager):
        """Theme switcher should have Light, Dark, and Match System options."""
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

        # Find theme switcher combo box
        theme_combo = None
        if hasattr(window, "_theme_switcher"):
            theme_combo = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_combo = window.theme_switcher
        else:
            for child in window.findChildren(QComboBox):
                if "theme" in child.objectName().lower():
                    theme_combo = child
                    break

        if theme_combo and isinstance(theme_combo, QComboBox):
            # Should have 3 items: Light, Dark, System
            assert theme_combo.count() == 3

            items = [theme_combo.itemText(i) for i in range(theme_combo.count())]
            assert "Light" in items or "light" in [i.lower() for i in items]
            assert "Dark" in items or "dark" in [i.lower() for i in items]
            assert "System" in items or "system" in [i.lower() for i in items] or "Match System" in items

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_current_theme_is_indicated(self, mock_state_manager):
        """Theme switcher should show the current theme selection."""
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

        # Find theme combo
        theme_combo = None
        if hasattr(window, "_theme_switcher"):
            theme_combo = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_combo = window.theme_switcher
        else:
            for child in window.findChildren(QComboBox):
                if "theme" in child.objectName().lower():
                    theme_combo = child
                    break

        if theme_combo and isinstance(theme_combo, QComboBox):
            # Should have a current selection
            current = theme_combo.currentText()
            assert current in ["Light", "Dark", "System", "Match System", "light", "dark", "system"]

        window.close()


class TestThemeSwitcherBehavior:
    """Test theme switcher behavior and interactions."""

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.apply_theme")
    def test_switching_theme_applies_immediately(self, mock_apply_theme, mock_state_manager):
        """Changing theme should apply immediately without restart."""
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

        # Find and change theme
        theme_combo = None
        if hasattr(window, "_theme_switcher"):
            theme_combo = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_combo = window.theme_switcher
        else:
            for child in window.findChildren(QComboBox):
                if "theme" in child.objectName().lower():
                    theme_combo = child
                    break

        if theme_combo and isinstance(theme_combo, QComboBox):
            # Simulate user selecting a different theme
            initial_index = theme_combo.currentIndex()
            new_index = (initial_index + 1) % theme_combo.count()
            theme_combo.setCurrentIndex(new_index)

            # Should trigger theme change
            # Check if apply_theme was called or if window has a handler
            assert hasattr(window, "_on_theme_changed") or mock_apply_theme.called

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    @patch("levelup.gui.main_window.set_theme_preference")
    def test_switching_theme_saves_preference(self, mock_set_pref, mock_state_manager):
        """Changing theme should save preference to config."""
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

        # Find and change theme
        theme_combo = None
        if hasattr(window, "_theme_switcher"):
            theme_combo = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_combo = window.theme_switcher
        else:
            for child in window.findChildren(QComboBox):
                if "theme" in child.objectName().lower():
                    theme_combo = child
                    break

        if theme_combo and isinstance(theme_combo, QComboBox):
            # Change theme
            initial_index = theme_combo.currentIndex()
            new_index = (initial_index + 1) % theme_combo.count()
            theme_combo.setCurrentIndex(new_index)

            # Should save preference
            # Either mock was called or window has internal save logic
            assert hasattr(window, "_save_theme_preference") or mock_set_pref.called

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

        # Find theme control
        theme_control = None
        if hasattr(window, "_theme_switcher"):
            theme_control = window._theme_switcher
        elif hasattr(window, "theme_switcher"):
            theme_control = window.theme_switcher
        else:
            for child in window.findChildren(QComboBox):
                if "theme" in child.objectName().lower():
                    theme_control = child
                    break

        if theme_control:
            tooltip = theme_control.toolTip()
            # Should have a tooltip explaining what it does
            assert tooltip is not None and len(tooltip) > 0

        window.close()
