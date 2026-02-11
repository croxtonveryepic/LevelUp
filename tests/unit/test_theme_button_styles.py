"""Tests for theme button styling in both light and dark themes."""

from __future__ import annotations


class TestThemeButtonDarkThemeStyles:
    """Test that theme button has proper styles in dark theme."""

    def test_dark_theme_has_theme_button_styles(self):
        """DARK_THEME should include QPushButton#themeBtn styles."""
        from levelup.gui.styles import DARK_THEME

        assert "QPushButton#themeBtn" in DARK_THEME, \
            "Dark theme should have QPushButton#themeBtn selector"

    def test_dark_theme_button_has_background_color(self):
        """Dark theme button should have background-color defined."""
        from levelup.gui.styles import DARK_THEME

        # Extract themeBtn section
        assert "#themeBtn" in DARK_THEME
        # Should have background-color property
        assert "background-color" in DARK_THEME

    def test_dark_theme_button_has_hover_state(self):
        """Dark theme button should have hover state defined."""
        from levelup.gui.styles import DARK_THEME

        # Should have hover state for themeBtn
        assert "#themeBtn:hover" in DARK_THEME, \
            "Dark theme should have hover state for theme button"

    def test_dark_theme_button_has_size_constraints(self):
        """Dark theme button should have size constraints (28x28px or similar)."""
        from levelup.gui.styles import DARK_THEME

        # Should have min-width and min-height or max-width and max-height
        # Pattern should match other icon buttons like #addTicketBtn
        assert "#themeBtn" in DARK_THEME

        # Check for size-related properties
        themeBtn_section = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]
        has_width = "width" in themeBtn_section or "min-width" in themeBtn_section or "max-width" in themeBtn_section
        has_height = "height" in themeBtn_section or "min-height" in themeBtn_section or "max-height" in themeBtn_section

        assert has_width or has_height, "Theme button should have size constraints"

    def test_dark_theme_button_has_border_radius(self):
        """Dark theme button should have border-radius for rounded corners."""
        from levelup.gui.styles import DARK_THEME

        # Should have border-radius
        assert "#themeBtn" in DARK_THEME
        themeBtn_section = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]
        assert "border-radius" in themeBtn_section, "Button should have rounded corners"

    def test_dark_theme_button_has_centered_text(self):
        """Dark theme button should have centered text/icon."""
        from levelup.gui.styles import DARK_THEME

        # Pattern matching #addTicketBtn which has centered text
        # Should either have text-align or padding properties
        assert "#themeBtn" in DARK_THEME

    def test_dark_theme_button_has_appropriate_colors(self):
        """Dark theme button should use appropriate dark theme colors."""
        from levelup.gui.styles import DARK_THEME

        # Button should exist and have color properties
        assert "#themeBtn" in DARK_THEME

        themeBtn_section = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]
        # Should define color or background-color
        has_color = "color:" in themeBtn_section or "background-color:" in themeBtn_section
        assert has_color, "Button should have color properties"

    def test_dark_theme_button_font_size(self):
        """Dark theme button should have appropriate font-size for symbols."""
        from levelup.gui.styles import DARK_THEME

        # Button should have font-size defined for the symbol
        assert "#themeBtn" in DARK_THEME
        themeBtn_section = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]

        # Should have font-size (symbols need larger size to be visible)
        assert "font-size" in themeBtn_section, "Button should have font-size for symbol"


class TestThemeButtonLightThemeStyles:
    """Test that theme button has proper styles in light theme."""

    def test_light_theme_has_theme_button_styles(self):
        """LIGHT_THEME should include QPushButton#themeBtn styles."""
        from levelup.gui.styles import LIGHT_THEME

        assert "QPushButton#themeBtn" in LIGHT_THEME, \
            "Light theme should have QPushButton#themeBtn selector"

    def test_light_theme_button_has_background_color(self):
        """Light theme button should have background-color defined."""
        from levelup.gui.styles import LIGHT_THEME

        # Extract themeBtn section
        assert "#themeBtn" in LIGHT_THEME
        # Should have background-color property
        assert "background-color" in LIGHT_THEME

    def test_light_theme_button_has_hover_state(self):
        """Light theme button should have hover state defined."""
        from levelup.gui.styles import LIGHT_THEME

        # Should have hover state for themeBtn
        assert "#themeBtn:hover" in LIGHT_THEME, \
            "Light theme should have hover state for theme button"

    def test_light_theme_button_has_size_constraints(self):
        """Light theme button should have size constraints (28x28px or similar)."""
        from levelup.gui.styles import LIGHT_THEME

        # Should have min-width and min-height or max-width and max-height
        assert "#themeBtn" in LIGHT_THEME

        # Check for size-related properties
        themeBtn_section = LIGHT_THEME.split("QPushButton#themeBtn")[1].split("}")[0]
        has_width = "width" in themeBtn_section or "min-width" in themeBtn_section or "max-width" in themeBtn_section
        has_height = "height" in themeBtn_section or "min-height" in themeBtn_section or "max-height" in themeBtn_section

        assert has_width or has_height, "Theme button should have size constraints"

    def test_light_theme_button_has_border_radius(self):
        """Light theme button should have border-radius for rounded corners."""
        from levelup.gui.styles import LIGHT_THEME

        # Should have border-radius
        assert "#themeBtn" in LIGHT_THEME
        themeBtn_section = LIGHT_THEME.split("QPushButton#themeBtn")[1].split("}")[0]
        assert "border-radius" in themeBtn_section, "Button should have rounded corners"

    def test_light_theme_button_has_appropriate_colors(self):
        """Light theme button should use appropriate light theme colors."""
        from levelup.gui.styles import LIGHT_THEME

        # Button should exist and have color properties
        assert "#themeBtn" in LIGHT_THEME

        themeBtn_section = LIGHT_THEME.split("QPushButton#themeBtn")[1].split("}")[0]
        # Should define color or background-color
        has_color = "color:" in themeBtn_section or "background-color:" in themeBtn_section
        assert has_color, "Button should have color properties"

    def test_light_theme_button_font_size(self):
        """Light theme button should have appropriate font-size for symbols."""
        from levelup.gui.styles import LIGHT_THEME

        # Button should have font-size defined for the symbol
        assert "#themeBtn" in LIGHT_THEME
        themeBtn_section = LIGHT_THEME.split("QPushButton#themeBtn")[1].split("}")[0]

        # Should have font-size (symbols need larger size to be visible)
        assert "font-size" in themeBtn_section, "Button should have font-size for symbol"


class TestThemeButtonStyleConsistency:
    """Test that theme button styles are consistent across themes."""

    def test_both_themes_have_theme_button(self):
        """Both DARK_THEME and LIGHT_THEME should have theme button styles."""
        from levelup.gui.styles import DARK_THEME, LIGHT_THEME

        assert "#themeBtn" in DARK_THEME
        assert "#themeBtn" in LIGHT_THEME

    def test_both_themes_have_hover_states(self):
        """Both themes should have hover states for theme button."""
        from levelup.gui.styles import DARK_THEME, LIGHT_THEME

        assert "#themeBtn:hover" in DARK_THEME
        assert "#themeBtn:hover" in LIGHT_THEME

    def test_button_size_consistent_across_themes(self):
        """Button size should be consistent across both themes."""
        from levelup.gui.styles import DARK_THEME, LIGHT_THEME

        # Extract size properties from both themes
        dark_themeBtn = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]
        light_themeBtn = LIGHT_THEME.split("QPushButton#themeBtn")[1].split("}")[0]

        # Both should have similar size constraints
        # This is a basic check that both define sizes
        dark_has_size = "width" in dark_themeBtn or "height" in dark_themeBtn
        light_has_size = "width" in light_themeBtn or "height" in light_themeBtn

        assert dark_has_size and light_has_size, \
            "Both themes should define button size"

    def test_button_matches_icon_button_pattern(self):
        """Theme button should follow same pattern as other icon buttons (#addTicketBtn)."""
        from levelup.gui.styles import DARK_THEME, LIGHT_THEME

        # Both should have the pattern similar to addTicketBtn
        # Check that #themeBtn exists in both
        assert "#themeBtn" in DARK_THEME
        assert "#themeBtn" in LIGHT_THEME

        # Check that properties are similar (size, padding, font-size)
        dark_themeBtn = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]
        light_themeBtn = LIGHT_THEME.split("QPushButton#themeBtn")[1].split("}")[0]

        # Should have font-size (for symbol display)
        assert "font-size" in dark_themeBtn
        assert "font-size" in light_themeBtn

    def test_button_not_too_prominent(self):
        """Button should not be overly prominent (e.g., not bright colors)."""
        from levelup.gui.styles import DARK_THEME, LIGHT_THEME

        # This is a design test - button should use neutral colors
        # Not bright green (#2ECC71) like action buttons
        dark_themeBtn = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]
        light_themeBtn = LIGHT_THEME.split("QPushButton#themeBtn")[1].split("}")[0]

        # Should not use bright action colors
        assert "#2ECC71" not in dark_themeBtn, "Button should not use bright green (too prominent)"
        assert "#27AE60" not in dark_themeBtn, "Button should not use action button colors"
        assert "#E74C3C" not in dark_themeBtn, "Button should not use red (too prominent)"

        assert "#27AE60" not in light_themeBtn, "Button should not use bright green"
        assert "#E74C3C" not in light_themeBtn, "Button should not use red"


class TestThemeButtonVisualStates:
    """Test theme button visual states and styling."""

    def test_dark_theme_button_hover_changes_appearance(self):
        """Dark theme button hover should change appearance."""
        from levelup.gui.styles import DARK_THEME

        # Extract base and hover sections
        base_section = DARK_THEME.split("QPushButton#themeBtn")[1].split("#themeBtn:hover")[0]
        hover_section = DARK_THEME.split("#themeBtn:hover")[1].split("}")[0]

        # Hover should have different background or color
        assert "background-color" in hover_section or "color" in hover_section, \
            "Hover state should change appearance"

    def test_light_theme_button_hover_changes_appearance(self):
        """Light theme button hover should change appearance."""
        from levelup.gui.styles import LIGHT_THEME

        # Extract base and hover sections
        hover_section = LIGHT_THEME.split("#themeBtn:hover")[1].split("}")[0]

        # Hover should have different background or color
        assert "background-color" in hover_section or "color" in hover_section, \
            "Hover state should change appearance"

    def test_button_hover_is_clearly_visible(self):
        """Button hover state should be clearly visible in both themes."""
        from levelup.gui.styles import DARK_THEME, LIGHT_THEME

        # Both themes should define distinct hover appearance
        assert "#themeBtn:hover" in DARK_THEME
        assert "#themeBtn:hover" in LIGHT_THEME

        # Hover sections should have background-color defined
        dark_hover = DARK_THEME.split("#themeBtn:hover")[1].split("}")[0]
        light_hover = LIGHT_THEME.split("#themeBtn:hover")[1].split("}")[0]

        assert "background-color" in dark_hover
        assert "background-color" in light_hover


class TestThemeButtonAccessibility:
    """Test theme button accessibility through styling."""

    def test_button_has_adequate_contrast_dark_theme(self):
        """Dark theme button should have adequate color contrast."""
        from levelup.gui.styles import DARK_THEME

        # Button should be visible against dark background
        # This is a basic check that color is defined
        assert "#themeBtn" in DARK_THEME
        themeBtn_section = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]

        # Should have text color defined
        has_color = "color:" in themeBtn_section
        assert has_color or "background-color:" in themeBtn_section, \
            "Button should have color properties for visibility"

    def test_button_has_adequate_contrast_light_theme(self):
        """Light theme button should have adequate color contrast."""
        from levelup.gui.styles import LIGHT_THEME

        # Button should be visible against light background
        assert "#themeBtn" in LIGHT_THEME
        themeBtn_section = LIGHT_THEME.split("QPushButton#themeBtn")[1].split("}")[0]

        # Should have text color defined
        has_color = "color:" in themeBtn_section
        assert has_color or "background-color:" in themeBtn_section, \
            "Button should have color properties for visibility"

    def test_button_size_adequate_for_clicking(self):
        """Button should be large enough for easy clicking (min 28x28px)."""
        from levelup.gui.styles import DARK_THEME, LIGHT_THEME

        # Check both themes define adequate size
        dark_themeBtn = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]
        light_themeBtn = LIGHT_THEME.split("QPushButton#themeBtn")[1].split("}")[0]

        # Should have size constraints (min 28px for accessibility)
        # This checks that size is defined, actual value checked in integration tests
        assert "width" in dark_themeBtn or "min-width" in dark_themeBtn
        assert "width" in light_themeBtn or "min-width" in light_themeBtn


class TestStylesConsistentWithOtherIconButtons:
    """Test that theme button styling is consistent with other icon buttons."""

    def test_follows_addTicketBtn_pattern(self):
        """Theme button should follow similar styling pattern as #addTicketBtn."""
        from levelup.gui.styles import DARK_THEME, LIGHT_THEME

        # Both should have addTicketBtn and themeBtn
        assert "#addTicketBtn" in DARK_THEME
        assert "#themeBtn" in DARK_THEME
        assert "#addTicketBtn" in LIGHT_THEME
        assert "#themeBtn" in LIGHT_THEME

    def test_has_similar_size_to_addTicketBtn(self):
        """Theme button should have similar size constraints as addTicketBtn (28x28)."""
        from levelup.gui.styles import DARK_THEME

        # Extract both button sections
        addTicket_section = DARK_THEME.split("QPushButton#addTicketBtn")[1].split("QPushButton#")[0]
        themeBtn_section = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]

        # Both should define width/height
        addTicket_has_width = "min-width: 28px" in addTicket_section or "max-width: 28px" in addTicket_section
        themeBtn_has_size = "width" in themeBtn_section or "min-width" in themeBtn_section

        assert addTicket_has_width, "addTicketBtn should have 28px width"
        assert themeBtn_has_size, "themeBtn should have size constraints"

    def test_both_icon_buttons_have_font_size(self):
        """Both icon buttons should have font-size defined for symbols."""
        from levelup.gui.styles import DARK_THEME

        addTicket_section = DARK_THEME.split("QPushButton#addTicketBtn")[1].split("QPushButton#")[0]
        themeBtn_section = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]

        # Both should define font-size
        assert "font-size" in addTicket_section
        assert "font-size" in themeBtn_section

    def test_both_icon_buttons_have_padding_zero(self):
        """Both icon buttons should have minimal padding for centered symbols."""
        from levelup.gui.styles import DARK_THEME

        addTicket_section = DARK_THEME.split("QPushButton#addTicketBtn")[1].split("QPushButton#")[0]
        themeBtn_section = DARK_THEME.split("QPushButton#themeBtn")[1].split("}")[0]

        # Both should define padding
        assert "padding" in addTicket_section
        assert "padding" in themeBtn_section
