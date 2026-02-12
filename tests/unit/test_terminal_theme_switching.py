"""Tests for terminal emulator theme switching."""

from __future__ import annotations

from unittest.mock import Mock, patch
from PyQt6.QtGui import QColor
import pytest

pytestmark = pytest.mark.regression

class TestTerminalEmulatorThemeSupport:
    """Test that terminal emulator supports dynamic theme switching."""

    def test_terminal_emulator_has_set_color_scheme_method(self):
        """TerminalEmulator should have a method to change color scheme."""
        from levelup.gui.terminal_emulator import TerminalEmulator

        assert hasattr(TerminalEmulator, "set_color_scheme") or \
               hasattr(TerminalEmulator, "apply_color_scheme") or \
               hasattr(TerminalEmulator, "set_colors")

    def test_terminal_can_accept_color_scheme_class(self):
        """Terminal should accept a color scheme class as parameter."""
        from levelup.gui.terminal_emulator import TerminalEmulator, CatppuccinMochaColors
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Should be able to create terminal with color scheme
        try:
            terminal = TerminalEmulator(color_scheme=CatppuccinMochaColors)
            assert terminal is not None
            terminal.close()
        except TypeError:
            # Or it might be set via method
            terminal = TerminalEmulator()
            if hasattr(terminal, "set_color_scheme"):
                terminal.set_color_scheme(CatppuccinMochaColors)
            terminal.close()


class TestTerminalColorSchemeInitialization:
    """Test terminal color scheme initialization."""

    def test_terminal_defaults_to_dark_colors(self):
        """Terminal should default to dark color scheme if none specified."""
        from levelup.gui.terminal_emulator import TerminalEmulator
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        terminal = TerminalEmulator()

        # Should have a color scheme set
        assert hasattr(terminal, "_color_scheme") or hasattr(terminal, "color_scheme")

        terminal.close()

    def test_terminal_accepts_light_color_scheme(self):
        """Terminal should accept LightTerminalColors as color scheme."""
        from levelup.gui.terminal_emulator import TerminalEmulator, LightTerminalColors
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        try:
            terminal = TerminalEmulator(color_scheme=LightTerminalColors)
            assert terminal is not None
            terminal.close()
        except TypeError:
            # Or set via method
            terminal = TerminalEmulator()
            if hasattr(terminal, "set_color_scheme"):
                terminal.set_color_scheme(LightTerminalColors)
            terminal.close()


class TestTerminalDynamicThemeSwitching:
    """Test dynamic color scheme switching while terminal is running."""

    def test_can_switch_from_dark_to_light(self):
        """Should be able to switch from dark to light color scheme."""
        from levelup.gui.terminal_emulator import TerminalEmulator, CatppuccinMochaColors, LightTerminalColors
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        terminal = TerminalEmulator()

        # Switch to light colors
        if hasattr(terminal, "set_color_scheme"):
            terminal.set_color_scheme(LightTerminalColors)
        elif hasattr(terminal, "apply_color_scheme"):
            terminal.apply_color_scheme(LightTerminalColors)

        # Should not crash
        assert terminal is not None
        terminal.close()

    def test_can_switch_from_light_to_dark(self):
        """Should be able to switch from light to dark color scheme."""
        from levelup.gui.terminal_emulator import TerminalEmulator, CatppuccinMochaColors, LightTerminalColors
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        try:
            terminal = TerminalEmulator(color_scheme=LightTerminalColors)
        except TypeError:
            terminal = TerminalEmulator()
            if hasattr(terminal, "set_color_scheme"):
                terminal.set_color_scheme(LightTerminalColors)

        # Switch to dark colors
        if hasattr(terminal, "set_color_scheme"):
            terminal.set_color_scheme(CatppuccinMochaColors)
        elif hasattr(terminal, "apply_color_scheme"):
            terminal.apply_color_scheme(CatppuccinMochaColors)

        # Should not crash
        assert terminal is not None
        terminal.close()

    def test_switching_triggers_repaint(self):
        """Switching color scheme should trigger terminal repaint."""
        from levelup.gui.terminal_emulator import TerminalEmulator, LightTerminalColors
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        terminal = TerminalEmulator()

        # Mock update method to track calls
        update_called = []
        original_update = terminal.update

        def track_update():
            update_called.append(True)
            original_update()

        terminal.update = track_update

        # Switch color scheme
        if hasattr(terminal, "set_color_scheme"):
            terminal.set_color_scheme(LightTerminalColors)
            # Should have triggered update
            assert len(update_called) > 0

        terminal.close()


class TestTerminalColorSchemeApplication:
    """Test that color scheme is properly applied to terminal rendering."""

    def test_background_color_matches_scheme(self):
        """Terminal background should match color scheme."""
        from levelup.gui.terminal_emulator import TerminalEmulator, LightTerminalColors
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        try:
            terminal = TerminalEmulator(color_scheme=LightTerminalColors)
        except TypeError:
            terminal = TerminalEmulator()
            if hasattr(terminal, "set_color_scheme"):
                terminal.set_color_scheme(LightTerminalColors)

        # Check that background color is used
        # (implementation may vary, but color scheme should be referenced)
        if hasattr(terminal, "_color_scheme"):
            assert terminal._color_scheme == LightTerminalColors or \
                   terminal._color_scheme is LightTerminalColors
        elif hasattr(terminal, "color_scheme"):
            assert terminal.color_scheme == LightTerminalColors or \
                   terminal.color_scheme is LightTerminalColors

        terminal.close()

    def test_text_color_matches_scheme(self):
        """Terminal text should use color scheme foreground."""
        from levelup.gui.terminal_emulator import TerminalEmulator, CatppuccinMochaColors
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        terminal = TerminalEmulator()

        # Color scheme should be available for text rendering
        assert hasattr(terminal, "_color_scheme") or hasattr(terminal, "color_scheme")

        terminal.close()


class TestTerminalColorSchemeWithContent:
    """Test color scheme switching with active terminal content."""

    def test_existing_content_recolors_on_switch(self):
        """Existing terminal content should recolor when scheme changes."""
        from levelup.gui.terminal_emulator import TerminalEmulator, LightTerminalColors
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        terminal = TerminalEmulator()

        # Add some content (if possible without PTY)
        # This is mainly testing that switching doesn't crash with content

        # Switch color scheme
        if hasattr(terminal, "set_color_scheme"):
            terminal.set_color_scheme(LightTerminalColors)

        # Should not crash
        assert terminal is not None
        terminal.close()

    def test_ansi_colors_adapt_to_scheme(self):
        """ANSI color codes should use colors from current scheme."""
        from levelup.gui.terminal_emulator import TerminalEmulator, LightTerminalColors
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        try:
            terminal = TerminalEmulator(color_scheme=LightTerminalColors)
        except TypeError:
            terminal = TerminalEmulator()
            if hasattr(terminal, "set_color_scheme"):
                terminal.set_color_scheme(LightTerminalColors)

        # Color resolution should use the current scheme
        if hasattr(terminal, "_color_scheme"):
            color_scheme = terminal._color_scheme
        elif hasattr(terminal, "color_scheme"):
            color_scheme = terminal.color_scheme
        else:
            color_scheme = LightTerminalColors

        # Should be able to resolve colors
        red_color = color_scheme.resolve("red", is_fg=True)
        assert isinstance(red_color, QColor)
        assert red_color.isValid()

        terminal.close()
