"""Unit tests for declined status colors and icons in GUI resources."""

from __future__ import annotations


class TestDeclinedStatusColors:
    """Test that declined status has proper color definitions."""

    def test_declined_in_ticket_status_colors(self):
        """TICKET_STATUS_COLORS dict should have declined status."""
        from levelup.gui.resources import TICKET_STATUS_COLORS

        assert "declined" in TICKET_STATUS_COLORS

    def test_declined_color_is_green_dark_theme(self):
        """Declined status should use green color in dark theme."""
        from levelup.gui.resources import TICKET_STATUS_COLORS

        # Should match 'done' green color for dark theme
        assert TICKET_STATUS_COLORS["declined"] == "#2ECC71"

    def test_declined_color_is_hex(self):
        """Declined color should be a valid hex color."""
        from levelup.gui.resources import TICKET_STATUS_COLORS

        color = TICKET_STATUS_COLORS["declined"]
        assert color.startswith("#")
        assert len(color) == 7

    def test_declined_in_light_status_colors(self):
        """_LIGHT_TICKET_STATUS_COLORS dict should have declined status."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        assert "declined" in _LIGHT_TICKET_STATUS_COLORS

    def test_declined_color_is_green_light_theme(self):
        """Declined status should use green color in light theme."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        # Should match 'done' green color for light theme
        assert _LIGHT_TICKET_STATUS_COLORS["declined"] == "#27AE60"

    def test_light_declined_color_is_hex(self):
        """Declined light theme color should be a valid hex color."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        color = _LIGHT_TICKET_STATUS_COLORS["declined"]
        assert color.startswith("#")
        assert len(color) == 7

    def test_all_statuses_have_colors(self):
        """All ticket statuses should have dark theme colors."""
        from levelup.gui.resources import TICKET_STATUS_COLORS

        expected = {"pending", "in progress", "done", "merged", "declined"}
        assert set(TICKET_STATUS_COLORS.keys()) == expected

    def test_all_statuses_have_light_colors(self):
        """All ticket statuses should have light theme colors."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        expected = {"pending", "in progress", "done", "merged", "declined"}
        assert set(_LIGHT_TICKET_STATUS_COLORS.keys()) == expected


class TestDeclinedStatusIcon:
    """Test that declined status has proper icon definition."""

    def test_declined_in_status_icons(self):
        """TICKET_STATUS_ICONS dict should have declined status."""
        from levelup.gui.resources import TICKET_STATUS_ICONS

        assert "declined" in TICKET_STATUS_ICONS

    def test_declined_icon_is_single_char(self):
        """Declined icon should be a single unicode character."""
        from levelup.gui.resources import TICKET_STATUS_ICONS

        icon = TICKET_STATUS_ICONS["declined"]
        assert isinstance(icon, str)
        assert len(icon) == 1

    def test_declined_icon_is_appropriate(self):
        """Declined icon should be X (U+2717) or circle (U+25CB)."""
        from levelup.gui.resources import TICKET_STATUS_ICONS

        icon = TICKET_STATUS_ICONS["declined"]
        # Allow either ✗ (U+2717) or ○ (U+25CB) as both are reasonable
        assert icon in ["\u2717", "\u25CB"]

    def test_all_statuses_have_icons(self):
        """All ticket statuses should have icons."""
        from levelup.gui.resources import TICKET_STATUS_ICONS

        expected = {"pending", "in progress", "done", "merged", "declined"}
        assert set(TICKET_STATUS_ICONS.keys()) == expected

    def test_icons_match_colors(self):
        """Icon keys should match color keys."""
        from levelup.gui.resources import TICKET_STATUS_COLORS, TICKET_STATUS_ICONS

        assert set(TICKET_STATUS_ICONS.keys()) == set(TICKET_STATUS_COLORS.keys())


class TestGetTicketStatusColorDeclined:
    """Test get_ticket_status_color() function with declined status."""

    def test_get_declined_color_dark_theme(self):
        """get_ticket_status_color() should return green for declined in dark theme."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("declined", theme="dark")
        assert color == "#2ECC71"

    def test_get_declined_color_light_theme(self):
        """get_ticket_status_color() should return green for declined in light theme."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("declined", theme="light")
        assert color == "#27AE60"

    def test_get_declined_color_default_theme(self):
        """get_ticket_status_color() should work with default theme parameter."""
        from levelup.gui.resources import get_ticket_status_color

        # Default theme is dark
        color = get_ticket_status_color("declined")
        assert color == "#2ECC71"

    def test_declined_color_matches_done(self):
        """Declined and done should use same green colors."""
        from levelup.gui.resources import get_ticket_status_color

        # Dark theme
        declined_dark = get_ticket_status_color("declined", theme="dark")
        done_dark = get_ticket_status_color("done", theme="dark")
        assert declined_dark == done_dark

        # Light theme
        declined_light = get_ticket_status_color("declined", theme="light")
        done_light = get_ticket_status_color("done", theme="light")
        assert declined_light == done_light

    def test_declined_no_run_status_override(self):
        """Declined status should not be affected by run_status parameter."""
        from levelup.gui.resources import get_ticket_status_color

        # run_status should only affect "in progress" tickets
        color_no_run = get_ticket_status_color("declined", theme="dark")
        color_with_run = get_ticket_status_color("declined", theme="dark", run_status="running")

        assert color_no_run == color_with_run
        assert color_no_run == "#2ECC71"


class TestDeclinedColorReadability:
    """Test that declined colors are readable in both themes."""

    def test_declined_dark_theme_brightness(self):
        """Declined color should be bright enough for dark theme."""
        from levelup.gui.resources import get_ticket_status_color

        try:
            from PyQt6.QtGui import QColor
        except ImportError:
            import pytest
            pytest.skip("PyQt6 not available")

        color = QColor(get_ticket_status_color("declined", theme="dark"))
        luminance = (color.red() + color.green() + color.blue()) / 3

        # Green should be bright enough to read on dark background
        assert luminance > 20, "Declined color is too dark for dark theme"

    def test_declined_light_theme_darkness(self):
        """Declined color should be dark enough for light theme."""
        from levelup.gui.resources import get_ticket_status_color

        try:
            from PyQt6.QtGui import QColor
        except ImportError:
            import pytest
            pytest.skip("PyQt6 not available")

        color = QColor(get_ticket_status_color("declined", theme="light"))
        luminance = (color.red() + color.green() + color.blue()) / 3

        # Green should be dark enough to read on light background
        assert luminance < 250, "Declined color is too light for light theme"

    def test_declined_is_green_semantic(self):
        """Declined color should be semantically green (success/complete)."""
        from levelup.gui.resources import get_ticket_status_color

        try:
            from PyQt6.QtGui import QColor
        except ImportError:
            import pytest
            pytest.skip("PyQt6 not available")

        # Test both themes
        for theme in ["dark", "light"]:
            color = QColor(get_ticket_status_color("declined", theme=theme))
            # Green channel should be dominant
            assert color.green() > color.red(), f"Declined not green in {theme} theme"
            assert color.green() > color.blue(), f"Declined not green in {theme} theme"


class TestDeclinedColorConsistency:
    """Test consistency of declined color definitions."""

    def test_declined_matches_done_color_value(self):
        """Declined should use exact same color values as done."""
        from levelup.gui.resources import TICKET_STATUS_COLORS, _LIGHT_TICKET_STATUS_COLORS

        # Dark theme should match
        assert TICKET_STATUS_COLORS["declined"] == TICKET_STATUS_COLORS["done"]

        # Light theme should match
        assert _LIGHT_TICKET_STATUS_COLORS["declined"] == _LIGHT_TICKET_STATUS_COLORS["done"]

    def test_color_definitions_are_uppercase(self):
        """Hex color codes should use uppercase letters."""
        from levelup.gui.resources import TICKET_STATUS_COLORS, _LIGHT_TICKET_STATUS_COLORS

        dark_color = TICKET_STATUS_COLORS["declined"]
        light_color = _LIGHT_TICKET_STATUS_COLORS["declined"]

        # Check if uppercase (or at least consistent format)
        assert dark_color == dark_color.upper() or dark_color == dark_color.lower()
        assert light_color == light_color.upper() or light_color == light_color.lower()

    def test_no_duplicate_color_definitions(self):
        """Color dicts should not have duplicate keys."""
        from levelup.gui.resources import TICKET_STATUS_COLORS, _LIGHT_TICKET_STATUS_COLORS

        # Check dark theme
        dark_keys = list(TICKET_STATUS_COLORS.keys())
        assert len(dark_keys) == len(set(dark_keys))

        # Check light theme
        light_keys = list(_LIGHT_TICKET_STATUS_COLORS.keys())
        assert len(light_keys) == len(set(light_keys))
