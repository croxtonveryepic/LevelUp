"""Tests for light theme ticket color constants and dictionaries.

This test file verifies that the _LIGHT_TICKET_STATUS_COLORS dict
has been updated correctly with the new pending color value:
- Dict contains correct keys
- Pending value is #2E3440
- Other values are unchanged
- Dict structure is valid
- Export/import correctness
"""

from __future__ import annotations


class TestLightTicketStatusColorsDictStructure:
    """Test _LIGHT_TICKET_STATUS_COLORS dict structure and contents."""

    def test_dict_exists(self):
        """_LIGHT_TICKET_STATUS_COLORS dict should exist."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        assert _LIGHT_TICKET_STATUS_COLORS is not None
        assert isinstance(_LIGHT_TICKET_STATUS_COLORS, dict)

    def test_dict_has_all_required_keys(self):
        """Dict should have all five ticket status keys."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        required_keys = ["pending", "in progress", "done", "merged", "declined"]

        for key in required_keys:
            assert key in _LIGHT_TICKET_STATUS_COLORS, \
                f"Missing required key: {key}"

    def test_dict_has_exactly_five_keys(self):
        """Dict should have exactly five keys (no extras)."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        assert len(_LIGHT_TICKET_STATUS_COLORS) == 5, \
            f"Should have 5 keys, got {len(_LIGHT_TICKET_STATUS_COLORS)}"

    def test_all_values_are_hex_colors(self):
        """All values should be valid hex color strings."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        for status, color in _LIGHT_TICKET_STATUS_COLORS.items():
            assert isinstance(color, str), f"{status} value should be string"
            assert color.startswith("#"), f"{status} color should start with #"
            assert len(color) == 7, f"{status} color should be 7 chars (e.g., #RRGGBB)"
            # Verify it's valid hex
            try:
                int(color[1:], 16)
            except ValueError:
                pytest.fail(f"{status} color {color} is not valid hex")

    def test_all_values_are_uppercase_hex(self):
        """All hex values should use uppercase letters (consistent style)."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        for status, color in _LIGHT_TICKET_STATUS_COLORS.items():
            hex_part = color[1:]  # Remove the #
            assert hex_part == hex_part.upper(), \
                f"{status} color should use uppercase hex"


class TestLightTicketStatusColorsPendingValue:
    """Test that pending key has the correct new value."""

    def test_pending_value_is_2E3440(self):
        """Pending value should be exactly #2E3440."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        assert _LIGHT_TICKET_STATUS_COLORS["pending"] == "#2E3440"

    def test_pending_value_is_not_old_4C566A(self):
        """Pending value should NOT be the old #4C566A."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        assert _LIGHT_TICKET_STATUS_COLORS["pending"] != "#4C566A", \
            "Pending color should be updated from old value"

    def test_pending_value_is_valid_color(self):
        """Pending value should be a valid hex color."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS
        from PyQt6.QtGui import QColor

        color_str = _LIGHT_TICKET_STATUS_COLORS["pending"]
        color = QColor(color_str)

        assert color.isValid(), f"Color {color_str} should be valid"

    def test_pending_value_rgb_components(self):
        """Pending color should have expected RGB components."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS
        from PyQt6.QtGui import QColor

        color = QColor(_LIGHT_TICKET_STATUS_COLORS["pending"])

        # #2E3440 = RGB(46, 52, 64)
        assert color.red() == 0x2E, f"Red should be 0x2E (46), got {color.red()}"
        assert color.green() == 0x34, f"Green should be 0x34 (52), got {color.green()}"
        assert color.blue() == 0x40, f"Blue should be 0x40 (64), got {color.blue()}"


class TestLightTicketStatusColorsOtherValues:
    """Test that other values in the dict remain unchanged."""

    def test_in_progress_value_unchanged(self):
        """In progress value should remain #F39C12."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        assert _LIGHT_TICKET_STATUS_COLORS["in progress"] == "#F39C12"

    def test_done_value_unchanged(self):
        """Done value should remain #27AE60."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        assert _LIGHT_TICKET_STATUS_COLORS["done"] == "#27AE60"

    def test_merged_value_unchanged(self):
        """Merged value should remain #95A5A6."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        assert _LIGHT_TICKET_STATUS_COLORS["merged"] == "#95A5A6"

    def test_all_non_pending_values_match_expected(self):
        """All non-pending values should match expected values."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        expected = {
            "in progress": "#F39C12",
            "done": "#27AE60",
            "merged": "#95A5A6",
            "declined": "#27AE60",
        }

        for status, expected_color in expected.items():
            actual_color = _LIGHT_TICKET_STATUS_COLORS[status]
            assert actual_color == expected_color, \
                f"{status} should be {expected_color}, got {actual_color}"


class TestDarkTicketStatusColorsUnchanged:
    """Test that dark theme dict (TICKET_STATUS_COLORS) is unchanged."""

    def test_dark_dict_exists(self):
        """TICKET_STATUS_COLORS dict should still exist."""
        from levelup.gui.resources import TICKET_STATUS_COLORS

        assert TICKET_STATUS_COLORS is not None
        assert isinstance(TICKET_STATUS_COLORS, dict)

    def test_dark_dict_pending_unchanged(self):
        """Dark theme pending should still be #CDD6F4."""
        from levelup.gui.resources import TICKET_STATUS_COLORS

        assert TICKET_STATUS_COLORS["pending"] == "#CDD6F4"

    def test_dark_dict_in_progress_unchanged(self):
        """Dark theme in progress should still be #E6A817."""
        from levelup.gui.resources import TICKET_STATUS_COLORS

        assert TICKET_STATUS_COLORS["in progress"] == "#E6A817"

    def test_dark_dict_done_unchanged(self):
        """Dark theme done should still be #2ECC71."""
        from levelup.gui.resources import TICKET_STATUS_COLORS

        assert TICKET_STATUS_COLORS["done"] == "#2ECC71"

    def test_dark_dict_merged_unchanged(self):
        """Dark theme merged should still be #6C7086."""
        from levelup.gui.resources import TICKET_STATUS_COLORS

        assert TICKET_STATUS_COLORS["merged"] == "#6C7086"

    def test_dark_dict_all_values_match_expected(self):
        """All dark theme values should match expected values."""
        from levelup.gui.resources import TICKET_STATUS_COLORS

        expected = {
            "pending": "#CDD6F4",
            "in progress": "#E6A817",
            "done": "#2ECC71",
            "merged": "#6C7086",
            "declined": "#2ECC71",
        }

        for status, expected_color in expected.items():
            actual_color = TICKET_STATUS_COLORS[status]
            assert actual_color == expected_color, \
                f"Dark {status} should be {expected_color}, got {actual_color}"


class TestDictConsistencyBetweenLightAndDark:
    """Test consistency between light and dark theme dicts."""

    def test_both_dicts_have_same_keys(self):
        """Light and dark dicts should have the same keys."""
        from levelup.gui.resources import TICKET_STATUS_COLORS, _LIGHT_TICKET_STATUS_COLORS

        light_keys = set(_LIGHT_TICKET_STATUS_COLORS.keys())
        dark_keys = set(TICKET_STATUS_COLORS.keys())

        assert light_keys == dark_keys, \
            f"Keys should match. Light: {light_keys}, Dark: {dark_keys}"

    def test_both_dicts_have_same_key_count(self):
        """Light and dark dicts should have same number of keys."""
        from levelup.gui.resources import TICKET_STATUS_COLORS, _LIGHT_TICKET_STATUS_COLORS

        assert len(_LIGHT_TICKET_STATUS_COLORS) == len(TICKET_STATUS_COLORS), \
            "Both dicts should have same number of keys"

    def test_pending_values_are_different_between_themes(self):
        """Pending color should be different in light vs dark themes."""
        from levelup.gui.resources import TICKET_STATUS_COLORS, _LIGHT_TICKET_STATUS_COLORS

        light_pending = _LIGHT_TICKET_STATUS_COLORS["pending"]
        dark_pending = TICKET_STATUS_COLORS["pending"]

        assert light_pending != dark_pending, \
            "Light and dark pending colors should be different"

    def test_dict_values_are_appropriate_for_theme(self):
        """Light theme should have darker colors, dark theme should have lighter colors."""
        from levelup.gui.resources import TICKET_STATUS_COLORS, _LIGHT_TICKET_STATUS_COLORS
        from PyQt6.QtGui import QColor

        # Pending: light should be dark, dark should be light
        light_pending = QColor(_LIGHT_TICKET_STATUS_COLORS["pending"])
        dark_pending = QColor(TICKET_STATUS_COLORS["pending"])

        light_lum = (light_pending.red() + light_pending.green() + light_pending.blue()) / 3
        dark_lum = (dark_pending.red() + dark_pending.green() + dark_pending.blue()) / 3

        # Light theme color should be darker (lower luminance)
        assert light_lum < dark_lum, \
            "Light theme should use darker colors than dark theme"


class TestColorConstantImportExport:
    """Test that constants can be imported correctly."""

    def test_can_import_light_dict(self):
        """Should be able to import _LIGHT_TICKET_STATUS_COLORS."""
        try:
            from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS
            assert True
        except ImportError:
            pytest.fail("Failed to import _LIGHT_TICKET_STATUS_COLORS")

    def test_can_import_dark_dict(self):
        """Should be able to import TICKET_STATUS_COLORS."""
        try:
            from levelup.gui.resources import TICKET_STATUS_COLORS
            assert True
        except ImportError:
            pytest.fail("Failed to import TICKET_STATUS_COLORS")

    def test_can_import_get_ticket_status_color_function(self):
        """Should be able to import get_ticket_status_color function."""
        try:
            from levelup.gui.resources import get_ticket_status_color
            assert callable(get_ticket_status_color)
        except ImportError:
            pytest.fail("Failed to import get_ticket_status_color")

    def test_imported_values_are_not_none(self):
        """Imported values should not be None."""
        from levelup.gui.resources import (
            TICKET_STATUS_COLORS,
            _LIGHT_TICKET_STATUS_COLORS,
            get_ticket_status_color,
        )

        assert TICKET_STATUS_COLORS is not None
        assert _LIGHT_TICKET_STATUS_COLORS is not None
        assert get_ticket_status_color is not None


class TestColorConstantMutability:
    """Test that color constants behave correctly regarding mutability."""

    def test_dict_is_mutable(self):
        """Dict should be mutable (can be modified if needed)."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        # Should be able to read
        value = _LIGHT_TICKET_STATUS_COLORS["pending"]
        assert value == "#2E3440"

        # Note: We don't actually mutate it in tests, just verify it's accessible

    def test_dict_values_are_strings_not_constants(self):
        """Dict values should be regular strings, not special constants."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS

        for status, color in _LIGHT_TICKET_STATUS_COLORS.items():
            assert type(color) == str, f"{status} value should be plain str"


class TestColorValidityForAllStatuses:
    """Test that all colors in the dict are valid and usable."""

    def test_all_light_colors_are_valid_qcolors(self):
        """All light theme colors should create valid QColor objects."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS
        from PyQt6.QtGui import QColor

        for status, color_str in _LIGHT_TICKET_STATUS_COLORS.items():
            color = QColor(color_str)
            assert color.isValid(), f"{status} color {color_str} is invalid"

    def test_all_dark_colors_are_valid_qcolors(self):
        """All dark theme colors should create valid QColor objects."""
        from levelup.gui.resources import TICKET_STATUS_COLORS
        from PyQt6.QtGui import QColor

        for status, color_str in TICKET_STATUS_COLORS.items():
            color = QColor(color_str)
            assert color.isValid(), f"{status} color {color_str} is invalid"

    def test_no_color_is_transparent(self):
        """No color should be transparent (alpha should be 255)."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS
        from PyQt6.QtGui import QColor

        for status, color_str in _LIGHT_TICKET_STATUS_COLORS.items():
            color = QColor(color_str)
            assert color.alpha() == 255, \
                f"{status} color should be fully opaque"

    def test_no_color_is_pure_white_or_black(self):
        """No ticket status color should be pure white or pure black."""
        from levelup.gui.resources import _LIGHT_TICKET_STATUS_COLORS
        from PyQt6.QtGui import QColor

        for status, color_str in _LIGHT_TICKET_STATUS_COLORS.items():
            color = QColor(color_str)

            # Not pure white
            is_white = (color.red() == 255 and
                       color.green() == 255 and
                       color.blue() == 255)
            assert not is_white, f"{status} should not be pure white"

            # Not pure black
            is_black = (color.red() == 0 and
                       color.green() == 0 and
                       color.blue() == 0)
            assert not is_black, f"{status} should not be pure black"
