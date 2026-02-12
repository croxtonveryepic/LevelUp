"""Tests for theme-aware color resources in gui/resources.py."""

from __future__ import annotations
import pytest

pytestmark = pytest.mark.regression

class TestThemeAwareStatusColors:
    """Test that status colors work in both light and dark themes."""

    def test_has_get_status_color_function(self):
        """Should have a function to get theme-aware status colors."""
        from levelup.gui.resources import get_status_color
        assert callable(get_status_color)

    def test_get_status_color_for_light_theme(self):
        """get_status_color() should return appropriate colors for light theme."""
        from levelup.gui.resources import get_status_color

        color = get_status_color("running", theme="light")
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7

    def test_get_status_color_for_dark_theme(self):
        """get_status_color() should return appropriate colors for dark theme."""
        from levelup.gui.resources import get_status_color

        color = get_status_color("running", theme="dark")
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7

    def test_all_statuses_have_light_theme_colors(self):
        """All status values should have light theme colors."""
        from levelup.gui.resources import get_status_color, STATUS_LABELS

        for status in STATUS_LABELS.keys():
            color = get_status_color(status, theme="light")
            assert color is not None
            assert isinstance(color, str)

    def test_all_statuses_have_dark_theme_colors(self):
        """All status values should have dark theme colors."""
        from levelup.gui.resources import get_status_color, STATUS_LABELS

        for status in STATUS_LABELS.keys():
            color = get_status_color(status, theme="dark")
            assert color is not None
            assert isinstance(color, str)

    def test_semantic_colors_preserved(self):
        """Semantic colors (green=success, red=error) should be preserved."""
        from levelup.gui.resources import get_status_color
        from PyQt6.QtGui import QColor

        # Completed should be green-ish in both themes
        completed_light = QColor(get_status_color("completed", theme="light"))
        completed_dark = QColor(get_status_color("completed", theme="dark"))

        # Green channel should be dominant
        assert completed_light.green() > completed_light.red()
        assert completed_dark.green() > completed_dark.red()

        # Failed should be red-ish in both themes
        failed_light = QColor(get_status_color("failed", theme="light"))
        failed_dark = QColor(get_status_color("failed", theme="dark"))

        # Red channel should be dominant
        assert failed_light.red() > failed_light.green()
        assert failed_dark.red() > failed_dark.green()

    def test_default_theme_parameter(self):
        """get_status_color() should have a default theme parameter."""
        from levelup.gui.resources import get_status_color

        # Should work without theme parameter
        color = get_status_color("running")
        assert isinstance(color, str)
        assert color.startswith("#")


class TestThemeAwareTicketStatusColors:
    """Test that ticket status colors work in both themes."""

    def test_has_get_ticket_status_color_function(self):
        """Should have a function to get theme-aware ticket status colors."""
        from levelup.gui.resources import get_ticket_status_color
        assert callable(get_ticket_status_color)

    def test_get_ticket_status_color_for_light_theme(self):
        """get_ticket_status_color() should return colors for light theme."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("done", theme="light")
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7

    def test_get_ticket_status_color_for_dark_theme(self):
        """get_ticket_status_color() should return colors for dark theme."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("done", theme="dark")
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7

    def test_all_ticket_statuses_have_light_colors(self):
        """All ticket statuses should have light theme colors."""
        from levelup.gui.resources import get_ticket_status_color, TICKET_STATUS_ICONS

        for status in TICKET_STATUS_ICONS.keys():
            color = get_ticket_status_color(status, theme="light")
            assert color is not None
            assert isinstance(color, str)

    def test_all_ticket_statuses_have_dark_colors(self):
        """All ticket statuses should have dark theme colors."""
        from levelup.gui.resources import get_ticket_status_color, TICKET_STATUS_ICONS

        for status in TICKET_STATUS_ICONS.keys():
            color = get_ticket_status_color(status, theme="dark")
            assert color is not None
            assert isinstance(color, str)

    def test_ticket_semantic_colors_preserved(self):
        """Ticket semantic colors should be preserved across themes."""
        from levelup.gui.resources import get_ticket_status_color
        from PyQt6.QtGui import QColor

        # Done should be green-ish in both themes
        done_light = QColor(get_ticket_status_color("done", theme="light"))
        done_dark = QColor(get_ticket_status_color("done", theme="dark"))

        assert done_light.green() > done_light.red()
        assert done_dark.green() > done_dark.red()


class TestLightThemeColorReadability:
    """Test that light theme colors are readable on light backgrounds."""

    def test_light_theme_status_colors_have_sufficient_darkness(self):
        """Status colors for light theme should be dark enough to read."""
        from levelup.gui.resources import get_status_color, STATUS_LABELS
        from PyQt6.QtGui import QColor

        for status in STATUS_LABELS.keys():
            color = QColor(get_status_color(status, theme="light"))
            # Calculate luminance
            luminance = (color.red() + color.green() + color.blue()) / 3
            # Should not be too light (white on white would be unreadable)
            # Allow some bright colors for semantic meaning (e.g., yellow warning)
            # But most should be reasonably visible
            assert luminance < 250, f"{status} color is too light for light theme"

    def test_light_theme_ticket_colors_are_readable(self):
        """Ticket status colors for light theme should be readable."""
        from levelup.gui.resources import get_ticket_status_color, TICKET_STATUS_ICONS
        from PyQt6.QtGui import QColor

        for status in TICKET_STATUS_ICONS.keys():
            color = QColor(get_ticket_status_color(status, theme="light"))
            luminance = (color.red() + color.green() + color.blue()) / 3
            # Should have reasonable contrast with light background
            assert luminance < 250, f"{status} color is too light for light theme"


class TestDarkThemeColorReadability:
    """Test that dark theme colors are readable on dark backgrounds."""

    def test_dark_theme_status_colors_have_sufficient_brightness(self):
        """Status colors for dark theme should be bright enough to read."""
        from levelup.gui.resources import get_status_color, STATUS_LABELS
        from PyQt6.QtGui import QColor

        for status in STATUS_LABELS.keys():
            color = QColor(get_status_color(status, theme="dark"))
            # Calculate luminance
            luminance = (color.red() + color.green() + color.blue()) / 3
            # Should not be too dark (black on black would be unreadable)
            # Most should be reasonably visible on dark background
            assert luminance > 20, f"{status} color is too dark for dark theme"

    def test_dark_theme_ticket_colors_are_readable(self):
        """Ticket status colors for dark theme should be readable."""
        from levelup.gui.resources import get_ticket_status_color, TICKET_STATUS_ICONS
        from PyQt6.QtGui import QColor

        for status in TICKET_STATUS_ICONS.keys():
            color = QColor(get_ticket_status_color(status, theme="dark"))
            luminance = (color.red() + color.green() + color.blue()) / 3
            # Should have reasonable contrast with dark background
            assert luminance > 20, f"{status} color is too dark for dark theme"


class TestBackwardCompatibility:
    """Test that existing color constants still work."""

    def test_status_colors_dict_still_exists(self):
        """Original STATUS_COLORS dict should still exist for compatibility."""
        from levelup.gui.resources import STATUS_COLORS
        assert STATUS_COLORS is not None
        assert isinstance(STATUS_COLORS, dict)

    def test_ticket_status_colors_dict_still_exists(self):
        """Original TICKET_STATUS_COLORS dict should still exist."""
        from levelup.gui.resources import TICKET_STATUS_COLORS
        assert TICKET_STATUS_COLORS is not None
        assert isinstance(TICKET_STATUS_COLORS, dict)

    def test_original_dicts_have_same_keys(self):
        """Original color dicts should have same keys as before."""
        from levelup.gui.resources import STATUS_COLORS, STATUS_LABELS

        # Should have entries for all status labels
        for status in STATUS_LABELS.keys():
            assert status in STATUS_COLORS

    def test_original_colors_are_valid(self):
        """Original color values should still be valid hex colors."""
        from levelup.gui.resources import STATUS_COLORS

        for status, color in STATUS_COLORS.items():
            assert isinstance(color, str)
            assert color.startswith("#")
            assert len(color) == 7
