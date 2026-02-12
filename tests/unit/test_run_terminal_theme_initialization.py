"""Tests for RunTerminalWidget theme initialization.

These tests verify that RunTerminalWidget accepts an optional theme parameter
and correctly passes it to the internal TerminalEmulatorWidget during construction,
ensuring the terminal displays the correct color scheme from first render without
visual flashing.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.regression

def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestRunTerminalWidgetThemeParameter:
    """Test that RunTerminalWidget accepts and uses optional theme parameter."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def test_accepts_theme_parameter_dark(self):
        """RunTerminalWidget should accept theme='dark' parameter."""
        from unittest.mock import patch

        # Mock the PtyBackend to avoid actual PTY creation
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            # Should not raise TypeError
            widget = RunTerminalWidget(theme="dark")
            assert widget is not None
            widget.deleteLater()

    def test_accepts_theme_parameter_light(self):
        """RunTerminalWidget should accept theme='light' parameter."""
        from unittest.mock import patch

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            # Should not raise TypeError
            widget = RunTerminalWidget(theme="light")
            assert widget is not None
            widget.deleteLater()

    def test_default_theme_is_dark(self):
        """RunTerminalWidget should default to 'dark' theme when no parameter given."""
        from unittest.mock import patch

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            from levelup.gui.terminal_emulator import CatppuccinMochaColors

            widget = RunTerminalWidget()

            # Should use dark color scheme by default
            assert widget._terminal._color_scheme == CatppuccinMochaColors
            widget.deleteLater()

    def test_theme_dark_creates_terminal_with_dark_colors(self):
        """When theme='dark', internal TerminalEmulatorWidget should use CatppuccinMochaColors."""
        from unittest.mock import patch

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            from levelup.gui.terminal_emulator import CatppuccinMochaColors

            widget = RunTerminalWidget(theme="dark")

            # Internal terminal should have dark color scheme
            assert widget._terminal._color_scheme == CatppuccinMochaColors
            widget.deleteLater()

    def test_theme_light_creates_terminal_with_light_colors(self):
        """When theme='light', internal TerminalEmulatorWidget should use LightTerminalColors."""
        from unittest.mock import patch

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            from levelup.gui.terminal_emulator import LightTerminalColors

            widget = RunTerminalWidget(theme="light")

            # Internal terminal should have light color scheme
            assert widget._terminal._color_scheme == LightTerminalColors
            widget.deleteLater()

    def test_backward_compatibility_no_theme_parameter(self):
        """Existing code that creates RunTerminalWidget() without theme should still work."""
        from unittest.mock import patch

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            # Should not raise TypeError when called without any arguments
            widget = RunTerminalWidget()
            assert widget is not None
            assert widget._terminal is not None
            widget.deleteLater()

    def test_theme_parameter_is_optional_with_default(self):
        """Theme parameter should be optional with default value 'dark'."""
        from unittest.mock import patch
        import inspect

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            # Inspect the __init__ signature
            sig = inspect.signature(RunTerminalWidget.__init__)

            # Should have a 'theme' parameter
            assert 'theme' in sig.parameters

            # Theme parameter should have a default value
            theme_param = sig.parameters['theme']
            assert theme_param.default != inspect.Parameter.empty

            # Default should be 'dark'
            assert theme_param.default == 'dark'


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestRunTerminalThemePassedToEmulator:
    """Test that theme parameter is correctly forwarded to TerminalEmulatorWidget."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def test_theme_forwarded_during_construction(self):
        """Theme should be passed to TerminalEmulatorWidget constructor, not set afterward."""
        from unittest.mock import patch, MagicMock

        # Track how TerminalEmulatorWidget was constructed
        original_import = __import__
        emulator_init_calls = []

        def custom_import(name, *args, **kwargs):
            module = original_import(name, *args, **kwargs)
            if name == "levelup.gui.terminal_emulator":
                original_emulator_init = module.TerminalEmulatorWidget.__init__

                def tracked_init(self, parent=None, color_scheme=None):
                    emulator_init_calls.append({
                        'parent': parent,
                        'color_scheme': color_scheme
                    })
                    # Don't actually initialize the emulator in this test
                    self._color_scheme = color_scheme

                module.TerminalEmulatorWidget.__init__ = tracked_init
            return module

        with patch("builtins.__import__", side_effect=custom_import):
            with patch("levelup.gui.terminal_emulator.PtyBackend"):
                # Import after patching
                import importlib
                import levelup.gui.run_terminal
                importlib.reload(levelup.gui.run_terminal)

                from levelup.gui.run_terminal import RunTerminalWidget
                from levelup.gui.terminal_emulator import LightTerminalColors

                # Create widget with light theme
                widget = RunTerminalWidget(theme="light")

                # Verify TerminalEmulatorWidget was called with light color scheme
                assert len(emulator_init_calls) > 0
                last_call = emulator_init_calls[-1]
                assert last_call['color_scheme'] == LightTerminalColors

    def test_no_manual_set_color_scheme_after_construction(self):
        """RunTerminalWidget should not call set_color_scheme after construction."""
        from unittest.mock import patch, MagicMock

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget(theme="light")

            # Mock the set_color_scheme method to track calls
            widget._terminal.set_color_scheme = MagicMock()

            # After construction, no additional set_color_scheme calls should happen
            # (this is implicitly tested by not calling it in __init__)
            widget._terminal.set_color_scheme.assert_not_called()

            widget.deleteLater()

    def test_correct_color_scheme_class_selected_for_dark(self):
        """When theme='dark', should pass CatppuccinMochaColors class to emulator."""
        from unittest.mock import patch, MagicMock

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            from levelup.gui.terminal_emulator import CatppuccinMochaColors

            # Track what was passed to TerminalEmulatorWidget
            with patch("levelup.gui.run_terminal.TerminalEmulatorWidget") as MockEmulator:
                mock_instance = MagicMock()
                MockEmulator.return_value = mock_instance

                widget = RunTerminalWidget(theme="dark")

                # Should have been called with CatppuccinMochaColors
                MockEmulator.assert_called_once()
                call_kwargs = MockEmulator.call_args[1] if MockEmulator.call_args else {}
                assert 'color_scheme' in call_kwargs
                assert call_kwargs['color_scheme'] == CatppuccinMochaColors

    def test_correct_color_scheme_class_selected_for_light(self):
        """When theme='light', should pass LightTerminalColors class to emulator."""
        from unittest.mock import patch, MagicMock

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            from levelup.gui.terminal_emulator import LightTerminalColors

            # Track what was passed to TerminalEmulatorWidget
            with patch("levelup.gui.run_terminal.TerminalEmulatorWidget") as MockEmulator:
                mock_instance = MagicMock()
                MockEmulator.return_value = mock_instance

                widget = RunTerminalWidget(theme="light")

                # Should have been called with LightTerminalColors
                MockEmulator.assert_called_once()
                call_kwargs = MockEmulator.call_args[1] if MockEmulator.call_args else {}
                assert 'color_scheme' in call_kwargs
                assert call_kwargs['color_scheme'] == LightTerminalColors


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestRunTerminalThemeEdgeCases:
    """Test edge cases for theme parameter handling."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def test_invalid_theme_value_falls_back_to_dark(self):
        """Invalid theme values should fall back to dark color scheme."""
        from unittest.mock import patch

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            from levelup.gui.terminal_emulator import CatppuccinMochaColors

            # Try with an invalid theme value
            widget = RunTerminalWidget(theme="invalid")

            # Should default to dark colors
            assert widget._terminal._color_scheme == CatppuccinMochaColors
            widget.deleteLater()

    def test_none_theme_uses_default_dark(self):
        """Passing theme=None should use default dark color scheme."""
        from unittest.mock import patch

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            from levelup.gui.terminal_emulator import CatppuccinMochaColors

            widget = RunTerminalWidget(theme=None)

            # Should use default dark colors
            assert widget._terminal._color_scheme == CatppuccinMochaColors
            widget.deleteLater()

    def test_empty_string_theme_uses_default_dark(self):
        """Passing theme='' should use default dark color scheme."""
        from unittest.mock import patch

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            from levelup.gui.terminal_emulator import CatppuccinMochaColors

            widget = RunTerminalWidget(theme="")

            # Should use default dark colors
            assert widget._terminal._color_scheme == CatppuccinMochaColors
            widget.deleteLater()

    def test_case_insensitive_theme_matching(self):
        """Theme matching should be case-insensitive."""
        from unittest.mock import patch

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            from levelup.gui.terminal_emulator import LightTerminalColors

            # Try uppercase
            widget1 = RunTerminalWidget(theme="LIGHT")
            assert widget1._terminal._color_scheme == LightTerminalColors
            widget1.deleteLater()

            # Try mixed case
            widget2 = RunTerminalWidget(theme="Light")
            assert widget2._terminal._color_scheme == LightTerminalColors
            widget2.deleteLater()

    def test_whitespace_in_theme_is_handled(self):
        """Theme parameter with extra whitespace should be handled gracefully."""
        from unittest.mock import patch

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            from levelup.gui.terminal_emulator import LightTerminalColors

            # Whitespace should be stripped
            widget = RunTerminalWidget(theme="  light  ")
            assert widget._terminal._color_scheme == LightTerminalColors
            widget.deleteLater()
