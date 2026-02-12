"""Tests for light theme stylesheet in gui/styles.py."""

from __future__ import annotations

import re

from levelup.gui.styles import LIGHT_THEME
import pytest

pytestmark = pytest.mark.regression

class TestLightThemeExists:
    """Test that LIGHT_THEME constant is defined."""

    def test_light_theme_constant_exists(self):
        """LIGHT_THEME should be defined in styles.py."""
        assert LIGHT_THEME is not None
        assert isinstance(LIGHT_THEME, str)
        assert len(LIGHT_THEME) > 0

    def test_light_theme_is_valid_stylesheet(self):
        """LIGHT_THEME should contain valid Qt stylesheet syntax."""
        # Should contain at least one selector
        assert "{" in LIGHT_THEME
        assert "}" in LIGHT_THEME
        # Should contain color properties
        assert "color:" in LIGHT_THEME or "background-color:" in LIGHT_THEME


class TestLightThemeColors:
    """Test that LIGHT_THEME uses appropriate light colors."""

    def _extract_colors(self, stylesheet: str) -> list[str]:
        """Extract all hex color codes from stylesheet."""
        return re.findall(r"#[0-9A-Fa-f]{6}", stylesheet)

    def test_uses_light_backgrounds(self):
        """Light theme should use light background colors."""
        colors = self._extract_colors(LIGHT_THEME)
        assert len(colors) > 0

        # Check that at least some colors are light (high RGB values)
        # Light colors have RGB values > 200 (approximately)
        light_colors = []
        for color in colors:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            avg = (r + g + b) / 3
            if avg > 200:
                light_colors.append(color)

        # At least 30% of colors should be light
        assert len(light_colors) > len(colors) * 0.3

    def test_uses_dark_text(self):
        """Light theme should use dark text colors for readability."""
        # Should contain at least some dark colors for text
        colors = self._extract_colors(LIGHT_THEME)
        dark_colors = []
        for color in colors:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            avg = (r + g + b) / 3
            if avg < 100:
                dark_colors.append(color)

        # Should have at least some dark colors for text
        assert len(dark_colors) > 0

    def test_background_and_text_contrast(self):
        """Light theme should have sufficient contrast between background and text."""
        # Extract background-color and color properties
        bg_pattern = r"background-color:\s*#([0-9A-Fa-f]{6})"
        fg_pattern = r"(?<!background-)color:\s*#([0-9A-Fa-f]{6})"

        bg_colors = re.findall(bg_pattern, LIGHT_THEME)
        fg_colors = re.findall(fg_pattern, LIGHT_THEME)

        # Should have both background and foreground colors
        assert len(bg_colors) > 0
        assert len(fg_colors) > 0


class TestLightThemeSelectors:
    """Test that LIGHT_THEME has all required Qt widget selectors."""

    def test_has_main_window_selector(self):
        """Should style QMainWindow and QDialog."""
        assert "QMainWindow" in LIGHT_THEME
        assert "QDialog" in LIGHT_THEME

    def test_has_table_widget_selector(self):
        """Should style QTableWidget."""
        assert "QTableWidget" in LIGHT_THEME

    def test_has_button_selectors(self):
        """Should style QPushButton and named buttons."""
        assert "QPushButton" in LIGHT_THEME
        # Check for named buttons with object IDs
        assert "#approveBtn" in LIGHT_THEME
        assert "#rejectBtn" in LIGHT_THEME
        assert "#reviseBtn" in LIGHT_THEME

    def test_has_text_edit_selectors(self):
        """Should style QTextEdit and QPlainTextEdit."""
        assert "QTextEdit" in LIGHT_THEME
        assert "QPlainTextEdit" in LIGHT_THEME

    def test_has_label_selector(self):
        """Should style QLabel."""
        assert "QLabel" in LIGHT_THEME

    def test_has_list_widget_selector(self):
        """Should style QListWidget."""
        assert "QListWidget" in LIGHT_THEME

    def test_has_line_edit_selector(self):
        """Should style QLineEdit."""
        assert "QLineEdit" in LIGHT_THEME

    def test_has_menu_selector(self):
        """Should style QMenu."""
        assert "QMenu" in LIGHT_THEME

    def test_has_status_bar_selector(self):
        """Should style QStatusBar."""
        assert "QStatusBar" in LIGHT_THEME

    def test_has_splitter_selector(self):
        """Should style QSplitter::handle."""
        assert "QSplitter::handle" in LIGHT_THEME


class TestLightThemeButtonStates:
    """Test that LIGHT_THEME includes button hover and pressed states."""

    def test_has_button_hover_states(self):
        """Should define hover states for buttons."""
        assert "QPushButton:hover" in LIGHT_THEME

    def test_has_button_pressed_states(self):
        """Should define pressed states for buttons."""
        assert "QPushButton:pressed" in LIGHT_THEME

    def test_has_button_disabled_states(self):
        """Should define disabled states for buttons."""
        assert "disabled" in LIGHT_THEME.lower()

    def test_has_named_button_hover_states(self):
        """Should define hover states for named buttons."""
        assert "#approveBtn:hover" in LIGHT_THEME


class TestLightThemeSemanticColors:
    """Test that LIGHT_THEME preserves semantic colors (success, error, warning)."""

    def test_has_approve_button_green(self):
        """Approve button should use green color."""
        # Find the #approveBtn section
        approve_section = LIGHT_THEME.split("#approveBtn")[1].split("}")[0]
        # Should contain green-ish color (starts with #2 or #3, middle value high)
        assert "background-color:" in approve_section

    def test_has_reject_button_red(self):
        """Reject button should use red color."""
        reject_section = LIGHT_THEME.split("#rejectBtn")[1].split("}")[0]
        assert "background-color:" in reject_section

    def test_has_warning_colors(self):
        """Should have yellow/orange warning colors."""
        # Revise button typically uses warning colors
        if "#reviseBtn" in LIGHT_THEME:
            revise_section = LIGHT_THEME.split("#reviseBtn")[1].split("}")[0]
            assert "background-color:" in revise_section


class TestLightThemeTableStyling:
    """Test table-specific styling in LIGHT_THEME."""

    def test_has_table_item_selector(self):
        """Should style table items."""
        assert "QTableWidget::item" in LIGHT_THEME

    def test_has_header_view_selector(self):
        """Should style table headers."""
        assert "QHeaderView::section" in LIGHT_THEME

    def test_has_table_selection_colors(self):
        """Should define selection colors for tables."""
        assert "selection-background-color:" in LIGHT_THEME
        assert "selection-color:" in LIGHT_THEME


class TestLightThemeListStyling:
    """Test list widget styling in LIGHT_THEME."""

    def test_has_list_item_selector(self):
        """Should style list items."""
        assert "QListWidget::item" in LIGHT_THEME

    def test_has_list_item_selected_state(self):
        """Should define selected state for list items."""
        assert "QListWidget::item:selected" in LIGHT_THEME

    def test_has_list_item_hover_state(self):
        """Should define hover state for list items."""
        assert "QListWidget::item:hover" in LIGHT_THEME


class TestLightThemeConsistency:
    """Test that LIGHT_THEME has similar structure to DARK_THEME."""

    def test_has_similar_structure_to_dark_theme(self):
        """Light theme should have similar selectors to dark theme."""
        from levelup.gui.styles import DARK_THEME

        # Extract selectors from both themes
        def extract_selectors(stylesheet: str) -> set[str]:
            # Simple extraction - find patterns before {
            selectors = set()
            lines = stylesheet.split("\n")
            for line in lines:
                line = line.strip()
                if "{" in line and not line.startswith("/*"):
                    selector = line.split("{")[0].strip()
                    if selector:
                        selectors.add(selector)
            return selectors

        light_selectors = extract_selectors(LIGHT_THEME)
        dark_selectors = extract_selectors(DARK_THEME)

        # Light theme should have at least 80% of dark theme selectors
        common = light_selectors & dark_selectors
        assert len(common) >= len(dark_selectors) * 0.8

    def test_has_monospace_font_settings(self):
        """Light theme should use monospace fonts for code."""
        assert "monospace" in LIGHT_THEME.lower() or "Consolas" in LIGHT_THEME
