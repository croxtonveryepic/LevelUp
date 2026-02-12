"""Tests for pending ticket color accessibility in light mode.

This test file covers requirements for improving pending ticket readability
in light mode by using a darker color with better contrast:
- Updated color provides WCAG AA compliant contrast ratio (4.5:1 minimum)
- Color change only affects light theme pending tickets
- Dark theme pending ticket color remains unchanged
- Theme-aware function returns correct color
- Edge cases and error conditions are handled
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.regression

class TestPendingTicketLightModeColorContrast:
    """Test pending ticket color meets WCAG AA contrast requirements in light mode."""

    def test_pending_color_is_darker_than_old_value_in_light_mode(self):
        """Pending ticket color in light mode should be darker than #4C566A for better readability."""
        from levelup.gui.resources import get_ticket_status_color
        from PyQt6.QtGui import QColor

        color_str = get_ticket_status_color("pending", theme="light")
        color = QColor(color_str)

        # Calculate luminance of new color
        new_luminance = (color.red() + color.green() + color.blue()) / 3

        # Old color #4C566A luminance
        old_color = QColor("#4C566A")
        old_luminance = (old_color.red() + old_color.green() + old_color.blue()) / 3

        # New color should be darker (lower luminance)
        assert new_luminance < old_luminance, \
            f"New pending color should be darker than #4C566A. Got {color_str}"

    def test_pending_light_mode_color_is_2E3440(self):
        """Pending ticket in light mode should use #2E3440 color."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("pending", theme="light")
        assert color == "#2E3440", \
            f"Expected pending light mode color to be #2E3440, got {color}"

    def test_pending_light_mode_meets_wcag_aa_contrast_ratio(self):
        """Pending ticket color should meet WCAG AA 4.5:1 contrast ratio against white."""
        from levelup.gui.resources import get_ticket_status_color
        from PyQt6.QtGui import QColor

        color_str = get_ticket_status_color("pending", theme="light")
        text_color = QColor(color_str)
        background_color = QColor("#FFFFFF")  # White background

        # Calculate relative luminance using WCAG formula
        def relative_luminance(color: QColor) -> float:
            """Calculate relative luminance for WCAG contrast ratio."""
            def srgb_to_linear(val: int) -> float:
                val_normalized = val / 255.0
                if val_normalized <= 0.03928:
                    return val_normalized / 12.92
                return ((val_normalized + 0.055) / 1.055) ** 2.4

            r = srgb_to_linear(color.red())
            g = srgb_to_linear(color.green())
            b = srgb_to_linear(color.blue())
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        text_lum = relative_luminance(text_color)
        bg_lum = relative_luminance(background_color)

        # Calculate contrast ratio
        if bg_lum > text_lum:
            contrast_ratio = (bg_lum + 0.05) / (text_lum + 0.05)
        else:
            contrast_ratio = (text_lum + 0.05) / (bg_lum + 0.05)

        # WCAG AA requires 4.5:1 for normal text
        assert contrast_ratio >= 4.5, \
            f"Contrast ratio {contrast_ratio:.2f}:1 does not meet WCAG AA requirement (4.5:1)"

    def test_pending_light_mode_color_is_visually_distinct_from_background(self):
        """Pending ticket color should be visually distinct from white background."""
        from levelup.gui.resources import get_ticket_status_color
        from PyQt6.QtGui import QColor

        color_str = get_ticket_status_color("pending", theme="light")
        color = QColor(color_str)

        # Color should be significantly darker than white
        # White is (255, 255, 255), expect pending to be much darker
        assert color.red() < 200, f"Red channel too bright: {color.red()}"
        assert color.green() < 200, f"Green channel too bright: {color.green()}"
        assert color.blue() < 200, f"Blue channel too bright: {color.blue()}"

    def test_old_color_4C566A_had_insufficient_contrast(self):
        """Verify that old color #4C566A had good but improvable contrast."""
        from PyQt6.QtGui import QColor

        # This test documents that while the old color passed WCAG AA,
        # the new color provides even better contrast for improved readability
        old_color = QColor("#4C566A")
        background_color = QColor("#FFFFFF")

        def relative_luminance(color: QColor) -> float:
            def srgb_to_linear(val: int) -> float:
                val_normalized = val / 255.0
                if val_normalized <= 0.03928:
                    return val_normalized / 12.92
                return ((val_normalized + 0.055) / 1.055) ** 2.4

            r = srgb_to_linear(color.red())
            g = srgb_to_linear(color.green())
            b = srgb_to_linear(color.blue())
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        text_lum = relative_luminance(old_color)
        bg_lum = relative_luminance(background_color)
        contrast_ratio = (bg_lum + 0.05) / (text_lum + 0.05)

        # Old color passed WCAG AA but we improved it further
        assert contrast_ratio >= 4.5, \
            f"Old color passed WCAG AA (got {contrast_ratio:.2f}:1)"


class TestPendingTicketDarkModeUnchanged:
    """Test that dark mode pending ticket color remains unchanged."""

    def test_pending_dark_mode_color_unchanged(self):
        """Pending ticket color in dark mode should still be #CDD6F4."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("pending", theme="dark")
        assert color == "#CDD6F4", \
            f"Dark mode pending color should remain #CDD6F4, got {color}"

    def test_pending_dark_mode_color_from_dict(self):
        """TICKET_STATUS_COLORS dict should have unchanged pending color."""
        from levelup.gui.resources import TICKET_STATUS_COLORS

        assert TICKET_STATUS_COLORS["pending"] == "#CDD6F4", \
            "Dark theme pending color constant should be #CDD6F4"

    def test_dark_mode_not_affected_by_light_mode_changes(self):
        """Dark mode should be completely independent of light mode changes."""
        from levelup.gui.resources import get_ticket_status_color

        # Get both colors
        light_color = get_ticket_status_color("pending", theme="light")
        dark_color = get_ticket_status_color("pending", theme="dark")

        # They should be different
        assert light_color != dark_color, \
            "Light and dark mode should have different pending colors"

        # Dark should still be the original
        assert dark_color == "#CDD6F4", \
            "Dark mode color should be unchanged"


class TestGetTicketStatusColorFunctionWithUpdatedPendingColor:
    """Test get_ticket_status_color() function with updated pending color."""

    def test_function_returns_new_color_for_pending_light(self):
        """get_ticket_status_color('pending', 'light') should return #2E3440."""
        from levelup.gui.resources import get_ticket_status_color

        result = get_ticket_status_color("pending", theme="light")
        assert result == "#2E3440"

    def test_function_returns_old_color_for_pending_dark(self):
        """get_ticket_status_color('pending', 'dark') should return #CDD6F4."""
        from levelup.gui.resources import get_ticket_status_color

        result = get_ticket_status_color("pending", theme="dark")
        assert result == "#CDD6F4"

    def test_function_maintains_backward_compatibility(self):
        """Function should still work for all other ticket statuses."""
        from levelup.gui.resources import get_ticket_status_color

        # Test that other statuses still work
        statuses = ["in progress", "done", "merged"]
        for status in statuses:
            light_result = get_ticket_status_color(status, theme="light")
            dark_result = get_ticket_status_color(status, theme="dark")

            assert isinstance(light_result, str)
            assert light_result.startswith("#")
            assert len(light_result) == 7

            assert isinstance(dark_result, str)
            assert dark_result.startswith("#")
            assert len(dark_result) == 7

    def test_function_handles_none_status(self):
        """Function should handle None status gracefully."""
        from levelup.gui.resources import get_ticket_status_color

        # Should return default color, not crash
        result = get_ticket_status_color(None, theme="light")  # type: ignore
        assert isinstance(result, str)
        assert result.startswith("#")

    def test_function_handles_empty_string_status(self):
        """Function should handle empty string status."""
        from levelup.gui.resources import get_ticket_status_color

        result = get_ticket_status_color("", theme="light")
        assert isinstance(result, str)
        assert result.startswith("#")

    def test_function_handles_invalid_status(self):
        """Function should handle invalid status strings."""
        from levelup.gui.resources import get_ticket_status_color

        result = get_ticket_status_color("invalid_status", theme="light")
        assert isinstance(result, str)
        assert result.startswith("#")

    def test_function_handles_invalid_theme(self):
        """Function should handle invalid theme strings."""
        from levelup.gui.resources import get_ticket_status_color

        # Should fall back to dark theme
        result = get_ticket_status_color("pending", theme="invalid")  # type: ignore
        assert isinstance(result, str)
        # Should use dark theme as fallback
        assert result == "#CDD6F4"

    def test_function_preserves_run_status_parameter(self):
        """Function should still accept and handle run_status parameter."""
        from levelup.gui.resources import get_ticket_status_color

        # Should not crash with run_status
        result = get_ticket_status_color(
            "in progress",
            theme="light",
            run_status="running"
        )
        assert isinstance(result, str)
        assert result.startswith("#")

    def test_pending_ignores_run_status_in_both_themes(self):
        """Pending tickets should ignore run_status in both light and dark themes."""
        from levelup.gui.resources import get_ticket_status_color

        # Light theme - should return new pending color regardless of run_status
        light_color = get_ticket_status_color(
            "pending",
            theme="light",
            run_status="running"
        )
        assert light_color == "#2E3440"

        # Dark theme - should return old pending color regardless of run_status
        dark_color = get_ticket_status_color(
            "pending",
            theme="dark",
            run_status="running"
        )
        assert dark_color == "#CDD6F4"


class TestLightTicketStatusColorsDict:
    """Test _LIGHT_TICKET_STATUS_COLORS dict has updated pending color."""

    def test_light_dict_has_pending_key(self):
        """_LIGHT_TICKET_STATUS_COLORS should have 'pending' key."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        assert "pending" in _LIGHT_TICKET_STATUS_COLORS

    def test_light_dict_pending_value_is_2E3440(self):
        """_LIGHT_TICKET_STATUS_COLORS['pending'] should be #2E3440."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        assert _LIGHT_TICKET_STATUS_COLORS["pending"] == "#2E3440"

    def test_light_dict_other_values_unchanged(self):
        """Other values in _LIGHT_TICKET_STATUS_COLORS should remain unchanged."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        # These are the expected values from the existing implementation
        expected = {
            "in progress": "#F39C12",
            "done": "#27AE60",
            "merged": "#95A5A6",
        }

        for status, expected_color in expected.items():
            assert _LIGHT_TICKET_STATUS_COLORS[status] == expected_color, \
                f"Status '{status}' color changed unexpectedly"


class TestAllPendingTicketsInLightMode:
    """Test that all pending tickets use the new color in light mode."""

    def test_multiple_pending_tickets_all_use_new_color(self):
        """All pending tickets should consistently use #2E3440 in light mode."""
        from levelup.gui.resources import get_ticket_status_color

        # Simulate multiple pending tickets
        for _ in range(10):
            color = get_ticket_status_color("pending", theme="light")
            assert color == "#2E3440", \
                "All pending tickets should use the same new color"

    def test_pending_color_consistent_across_function_calls(self):
        """Pending color should be consistent across multiple function calls."""
        from levelup.gui.resources import get_ticket_status_color

        colors = [
            get_ticket_status_color("pending", theme="light")
            for _ in range(100)
        ]

        # All should be the same
        assert all(c == "#2E3440" for c in colors), \
            "Color should be consistent across calls"


class TestColorChangeAppliesOnlyToPending:
    """Test that color change only affects pending status, not others."""

    def test_in_progress_light_color_unchanged(self):
        """In progress color in light mode should be unchanged."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("in progress", theme="light")
        assert color == "#F39C12", \
            "In progress light mode color should remain #F39C12"

    def test_done_light_color_unchanged(self):
        """Done color in light mode should be unchanged."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("done", theme="light")
        assert color == "#27AE60", \
            "Done light mode color should remain #27AE60"

    def test_merged_light_color_unchanged(self):
        """Merged color in light mode should be unchanged."""
        from levelup.gui.resources import get_ticket_status_color

        color = get_ticket_status_color("merged", theme="light")
        assert color == "#95A5A6", \
            "Merged light mode color should remain #95A5A6"

    def test_all_dark_theme_colors_unchanged(self):
        """All dark theme colors should remain unchanged."""
        from levelup.gui.resources import get_ticket_status_color

        expected_dark = {
            "pending": "#CDD6F4",
            "in progress": "#E6A817",
            "done": "#2ECC71",
            "merged": "#6C7086",
        }

        for status, expected_color in expected_dark.items():
            color = get_ticket_status_color(status, theme="dark")
            assert color == expected_color, \
                f"Dark theme {status} color should remain unchanged"


class TestUpdatedColorMatchesLightThemeTextColor:
    """Test that new pending color matches the light theme's main text color."""

    def test_pending_color_matches_light_theme_text_2E3440(self):
        """New pending color #2E3440 should match light theme's main text color."""
        from levelup.gui.resources import get_ticket_status_color

        pending_color = get_ticket_status_color("pending", theme="light")

        # According to project_context.md, light theme text color is #2E3440
        expected_text_color = "#2E3440"

        assert pending_color == expected_text_color, \
            "Pending color should match light theme's main text color for consistency"

    def test_new_color_provides_consistent_text_appearance(self):
        """New color should provide consistent text appearance across UI."""
        from levelup.gui.resources import get_ticket_status_color
        from PyQt6.QtGui import QColor

        pending_color_str = get_ticket_status_color("pending", theme="light")
        pending_color = QColor(pending_color_str)

        # #2E3440 is a dark blue-gray that's commonly used for text
        # Verify it has the expected RGB values
        expected = QColor("#2E3440")

        assert pending_color.red() == expected.red()
        assert pending_color.green() == expected.green()
        assert pending_color.blue() == expected.blue()
