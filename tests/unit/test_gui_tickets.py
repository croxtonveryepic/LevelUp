"""Tests for GUI ticket resources (no Qt dependency needed)."""

from __future__ import annotations

from levelup.gui.resources import TICKET_STATUS_COLORS, TICKET_STATUS_ICONS


class TestTicketStatusColors:
    def test_all_statuses_present(self):
        expected = {"pending", "in progress", "done", "merged", "declined"}
        assert set(TICKET_STATUS_COLORS.keys()) == expected

    def test_values_are_hex_colors(self):
        for status, color in TICKET_STATUS_COLORS.items():
            assert color.startswith("#"), f"{status} color {color!r} is not a hex color"
            assert len(color) == 7, f"{status} color {color!r} is not 7 chars"

    def test_pending_is_light(self):
        # Pending should be the default text color (light gray)
        assert TICKET_STATUS_COLORS["pending"] == "#CDD6F4"

    def test_done_is_green(self):
        assert TICKET_STATUS_COLORS["done"] == "#2ECC71"


class TestTicketStatusIcons:
    def test_all_statuses_present(self):
        expected = {"pending", "in progress", "done", "merged", "declined"}
        assert set(TICKET_STATUS_ICONS.keys()) == expected

    def test_keys_match_colors(self):
        assert set(TICKET_STATUS_ICONS.keys()) == set(TICKET_STATUS_COLORS.keys())

    def test_icons_are_single_chars(self):
        for status, icon in TICKET_STATUS_ICONS.items():
            assert len(icon) == 1, f"{status} icon {icon!r} is not a single char"

    def test_done_is_checkmark(self):
        assert TICKET_STATUS_ICONS["done"] == "\u2714"

    def test_pending_is_empty_circle(self):
        assert TICKET_STATUS_ICONS["pending"] == "\u25CB"
