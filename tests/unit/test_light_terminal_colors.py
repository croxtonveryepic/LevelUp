"""Tests for light terminal color scheme in gui/terminal_emulator.py."""

from __future__ import annotations

from PyQt6.QtGui import QColor


class TestLightTerminalColorsClass:
    """Test that LightTerminalColors class exists and is properly defined."""

    def test_class_exists(self):
        """LightTerminalColors class should be defined."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        assert LightTerminalColors is not None

    def test_has_background_color(self):
        """LightTerminalColors should have BG attribute."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        assert hasattr(LightTerminalColors, "BG")
        assert isinstance(LightTerminalColors.BG, QColor)

    def test_has_foreground_color(self):
        """LightTerminalColors should have FG attribute."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        assert hasattr(LightTerminalColors, "FG")
        assert isinstance(LightTerminalColors.FG, QColor)

    def test_has_cursor_color(self):
        """LightTerminalColors should have CURSOR attribute."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        assert hasattr(LightTerminalColors, "CURSOR")
        assert isinstance(LightTerminalColors.CURSOR, QColor)

    def test_has_selection_color(self):
        """LightTerminalColors should have SELECTION attribute."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        assert hasattr(LightTerminalColors, "SELECTION")
        assert isinstance(LightTerminalColors.SELECTION, QColor)


class TestLightTerminalColorsValues:
    """Test that light terminal colors use appropriate light palette."""

    def test_background_is_light(self):
        """Background should be a light color."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        bg = LightTerminalColors.BG
        # Light background should have high RGB values (> 200)
        assert bg.red() > 200 or bg.green() > 200 or bg.blue() > 200

    def test_foreground_is_dark(self):
        """Foreground should be a dark color for readability."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        fg = LightTerminalColors.FG
        # Dark text should have low RGB values (< 100)
        avg = (fg.red() + fg.green() + fg.blue()) / 3
        assert avg < 100

    def test_background_foreground_contrast(self):
        """Background and foreground should have sufficient contrast."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        bg = LightTerminalColors.BG
        fg = LightTerminalColors.FG

        # Calculate luminance difference
        bg_lum = (bg.red() + bg.green() + bg.blue()) / 3
        fg_lum = (fg.red() + fg.green() + fg.blue()) / 3
        contrast = abs(bg_lum - fg_lum)

        # Should have at least 150 points of contrast
        assert contrast > 150

    def test_cursor_is_visible(self):
        """Cursor color should be visible on light background."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        cursor = LightTerminalColors.CURSOR
        bg = LightTerminalColors.BG

        # Cursor should be different from background
        assert cursor != bg


class TestLightTerminalANSIColors:
    """Test that light terminal has ANSI color mappings."""

    def test_has_named_colors_dict(self):
        """LightTerminalColors should have _NAMED color dictionary."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        assert hasattr(LightTerminalColors, "_NAMED")
        assert isinstance(LightTerminalColors._NAMED, dict)

    def test_has_basic_ansi_colors(self):
        """Should have basic ANSI colors (black, red, green, etc.)."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        named = LightTerminalColors._NAMED

        basic_colors = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
        for color in basic_colors:
            assert color in named, f"Missing basic color: {color}"

    def test_has_bright_ansi_colors(self):
        """Should have bright ANSI colors (brightred, brightgreen, etc.)."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        named = LightTerminalColors._NAMED

        bright_colors = ["brightblack", "brightred", "brightgreen", "brightyellow",
                        "brightblue", "brightmagenta", "brightcyan", "brightwhite"]
        for color in bright_colors:
            assert color in named, f"Missing bright color: {color}"

    def test_ansi_colors_are_hex_strings(self):
        """ANSI color values should be hex color strings."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        named = LightTerminalColors._NAMED

        for name, color in named.items():
            assert isinstance(color, str), f"{name} is not a string"
            assert color.startswith("#"), f"{name} color {color} doesn't start with #"
            assert len(color) == 7, f"{name} color {color} is not 7 chars"

    def test_ansi_colors_adapted_for_light_background(self):
        """ANSI colors should be readable on light background."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        bg = LightTerminalColors.BG
        bg_lum = (bg.red() + bg.green() + bg.blue()) / 3

        # If background is light (> 200), then text colors should be darker
        if bg_lum > 200:
            named = LightTerminalColors._NAMED
            # Check that at least black is dark
            black_color = QColor(named["black"])
            black_lum = (black_color.red() + black_color.green() + black_color.blue()) / 3
            # Black should be significantly darker than background
            assert black_lum < bg_lum - 100


class TestLightTerminalColorsResolve:
    """Test the resolve() method for color resolution."""

    def test_has_resolve_method(self):
        """LightTerminalColors should have resolve() class method."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        assert hasattr(LightTerminalColors, "resolve")
        assert callable(LightTerminalColors.resolve)

    def test_resolve_default_foreground(self):
        """resolve('default', True) should return FG color."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        color = LightTerminalColors.resolve("default", is_fg=True)
        assert isinstance(color, QColor)
        assert color == LightTerminalColors.FG

    def test_resolve_default_background(self):
        """resolve('default', False) should return BG color."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        color = LightTerminalColors.resolve("default", is_fg=False)
        assert isinstance(color, QColor)
        assert color == LightTerminalColors.BG

    def test_resolve_named_color(self):
        """resolve() should handle named colors from _NAMED dict."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        color = LightTerminalColors.resolve("red", is_fg=True)
        assert isinstance(color, QColor)
        # Should return a valid color (not default)
        assert color.isValid()

    def test_resolve_hex_color(self):
        """resolve() should handle 6-digit hex colors."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        color = LightTerminalColors.resolve("FF0000", is_fg=True)
        assert isinstance(color, QColor)
        assert color.isValid()
        assert color.red() == 255
        assert color.green() == 0
        assert color.blue() == 0

    def test_resolve_prefixed_hex_color(self):
        """resolve() should handle #-prefixed hex colors."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        color = LightTerminalColors.resolve("#00FF00", is_fg=True)
        assert isinstance(color, QColor)
        assert color.isValid()
        assert color.green() == 255

    def test_resolve_empty_string_returns_default(self):
        """resolve('') should return default color."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        fg = LightTerminalColors.resolve("", is_fg=True)
        bg = LightTerminalColors.resolve("", is_fg=False)
        assert fg == LightTerminalColors.FG
        assert bg == LightTerminalColors.BG

    def test_resolve_invalid_color_returns_default(self):
        """resolve() should return default for invalid color strings."""
        from levelup.gui.terminal_emulator import LightTerminalColors
        color = LightTerminalColors.resolve("notacolor", is_fg=True)
        assert isinstance(color, QColor)
        # Should fall back to default
        assert color == LightTerminalColors.FG


class TestLightTerminalColorsStructure:
    """Test that LightTerminalColors has similar structure to CatppuccinMochaColors."""

    def test_has_same_attributes_as_dark_colors(self):
        """Light colors should have same attributes as dark colors."""
        from levelup.gui.terminal_emulator import CatppuccinMochaColors, LightTerminalColors

        # Both should have BG, FG, CURSOR, SELECTION
        for attr in ["BG", "FG", "CURSOR", "SELECTION"]:
            assert hasattr(LightTerminalColors, attr)
            assert hasattr(CatppuccinMochaColors, attr)

    def test_has_same_named_colors_as_dark_colors(self):
        """Light and dark color schemes should have same named color keys."""
        from levelup.gui.terminal_emulator import CatppuccinMochaColors, LightTerminalColors

        dark_keys = set(CatppuccinMochaColors._NAMED.keys())
        light_keys = set(LightTerminalColors._NAMED.keys())

        # Should have same set of color names
        assert dark_keys == light_keys

    def test_color_values_differ_from_dark_theme(self):
        """Light theme colors should be different from dark theme."""
        from levelup.gui.terminal_emulator import CatppuccinMochaColors, LightTerminalColors

        # Background colors should be different
        assert LightTerminalColors.BG != CatppuccinMochaColors.BG
        # Foreground colors should be different
        assert LightTerminalColors.FG != CatppuccinMochaColors.FG
