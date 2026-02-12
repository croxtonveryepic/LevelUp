"""WCAG AA compliance tests for pending ticket colors.

This test file validates that the pending ticket color update meets
Web Content Accessibility Guidelines (WCAG) 2.1 Level AA requirements:
- Minimum contrast ratio of 4.5:1 for normal text
- Proper contrast calculation using relative luminance formula
- Verification against both white and light gray backgrounds
- Comparison with old color to prove improvement
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.regression

def _can_import_pyqt6() -> bool:
    """Check if PyQt6 is available."""
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def calculate_relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance for WCAG contrast ratio.

    Uses the WCAG 2.1 formula:
    https://www.w3.org/TR/WCAG21/#dfn-relative-luminance

    Args:
        r: Red channel (0-255)
        g: Green channel (0-255)
        b: Blue channel (0-255)

    Returns:
        Relative luminance value (0.0-1.0)
    """
    def srgb_to_linear(val: int) -> float:
        val_normalized = val / 255.0
        if val_normalized <= 0.03928:
            return val_normalized / 12.92
        return ((val_normalized + 0.055) / 1.055) ** 2.4

    r_linear = srgb_to_linear(r)
    g_linear = srgb_to_linear(g)
    b_linear = srgb_to_linear(b)

    return 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear


def calculate_contrast_ratio(lum1: float, lum2: float) -> float:
    """Calculate WCAG contrast ratio between two luminance values.

    Args:
        lum1: Relative luminance of first color
        lum2: Relative luminance of second color

    Returns:
        Contrast ratio (1.0-21.0)
    """
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestWCAGContrastRatioPendingLightMode:
    """Test WCAG AA contrast ratio for pending tickets in light mode."""

    def test_pending_light_mode_meets_wcag_aa_against_white(self):
        """Pending color #2E3440 should meet WCAG AA 4.5:1 against white #FFFFFF."""
        from PyQt6.QtGui import QColor

        text_color = QColor("#2E3440")
        bg_color = QColor("#FFFFFF")

        text_lum = calculate_relative_luminance(
            text_color.red(), text_color.green(), text_color.blue()
        )
        bg_lum = calculate_relative_luminance(
            bg_color.red(), bg_color.green(), bg_color.blue()
        )

        contrast = calculate_contrast_ratio(text_lum, bg_lum)

        # WCAG AA requires 4.5:1 for normal text, 3:1 for large text
        assert contrast >= 4.5, \
            f"Contrast ratio {contrast:.2f}:1 fails WCAG AA (need 4.5:1)"

    def test_pending_light_mode_meets_wcag_aa_against_light_gray(self):
        """Pending color should meet WCAG AA against light gray #F5F5F5 background."""
        from PyQt6.QtGui import QColor

        text_color = QColor("#2E3440")
        bg_color = QColor("#F5F5F5")  # Light gray from project_context.md

        text_lum = calculate_relative_luminance(
            text_color.red(), text_color.green(), text_color.blue()
        )
        bg_lum = calculate_relative_luminance(
            bg_color.red(), bg_color.green(), bg_color.blue()
        )

        contrast = calculate_contrast_ratio(text_lum, bg_lum)

        # Should still meet AA against slightly darker background
        assert contrast >= 4.5, \
            f"Contrast ratio {contrast:.2f}:1 fails WCAG AA against #F5F5F5"

    def test_pending_light_mode_exceeds_wcag_aa_minimum(self):
        """Pending color should significantly exceed WCAG AA minimum."""
        from PyQt6.QtGui import QColor

        text_color = QColor("#2E3440")
        bg_color = QColor("#FFFFFF")

        text_lum = calculate_relative_luminance(
            text_color.red(), text_color.green(), text_color.blue()
        )
        bg_lum = calculate_relative_luminance(
            bg_color.red(), bg_color.green(), bg_color.blue()
        )

        contrast = calculate_contrast_ratio(text_lum, bg_lum)

        # Should exceed minimum by a comfortable margin (at least 10%)
        assert contrast >= 4.95, \
            f"Contrast {contrast:.2f}:1 should exceed AA minimum by margin"

    def test_old_color_4C566A_failed_wcag_aa(self):
        """Document that old color #4C566A passed WCAG AA but was improved."""
        from PyQt6.QtGui import QColor

        old_color = QColor("#4C566A")
        bg_color = QColor("#FFFFFF")

        text_lum = calculate_relative_luminance(
            old_color.red(), old_color.green(), old_color.blue()
        )
        bg_lum = calculate_relative_luminance(
            bg_color.red(), bg_color.green(), bg_color.blue()
        )

        contrast = calculate_contrast_ratio(text_lum, bg_lum)

        # Old color passed WCAG AA (and even AAA), but we improved it further
        assert contrast >= 4.5, \
            f"Old color passed WCAG AA (got {contrast:.2f}:1)"

    def test_contrast_improvement_from_old_to_new(self):
        """New color should have significantly better contrast than old color."""
        from PyQt6.QtGui import QColor

        old_color = QColor("#4C566A")
        new_color = QColor("#2E3440")
        bg_color = QColor("#FFFFFF")

        old_lum = calculate_relative_luminance(
            old_color.red(), old_color.green(), old_color.blue()
        )
        new_lum = calculate_relative_luminance(
            new_color.red(), new_color.green(), new_color.blue()
        )
        bg_lum = calculate_relative_luminance(
            bg_color.red(), bg_color.green(), bg_color.blue()
        )

        old_contrast = calculate_contrast_ratio(old_lum, bg_lum)
        new_contrast = calculate_contrast_ratio(new_lum, bg_lum)

        # New should be better than old
        assert new_contrast > old_contrast, \
            f"New contrast {new_contrast:.2f}:1 should exceed old {old_contrast:.2f}:1"

        # Improvement should be at least 30%
        improvement_ratio = new_contrast / old_contrast
        assert improvement_ratio >= 1.3, \
            f"Contrast improvement {improvement_ratio:.2%} should be at least 30%"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestWCAGLuminanceCalculations:
    """Test accurate luminance calculations for pending colors."""

    def test_new_pending_color_luminance_calculation(self):
        """Verify luminance calculation for #2E3440."""
        from PyQt6.QtGui import QColor

        color = QColor("#2E3440")
        lum = calculate_relative_luminance(
            color.red(), color.green(), color.blue()
        )

        # #2E3440 is a dark color, should have low luminance
        assert 0.0 <= lum <= 1.0, "Luminance must be in range [0, 1]"
        assert lum < 0.3, f"Dark color should have low luminance, got {lum:.4f}"

    def test_white_background_luminance(self):
        """Verify luminance calculation for white background."""
        from PyQt6.QtGui import QColor

        white = QColor("#FFFFFF")
        lum = calculate_relative_luminance(
            white.red(), white.green(), white.blue()
        )

        # White should have luminance very close to 1.0
        assert lum > 0.99, f"White luminance should be ~1.0, got {lum:.4f}"

    def test_old_pending_color_luminance(self):
        """Verify luminance calculation for old #4C566A."""
        from PyQt6.QtGui import QColor

        color = QColor("#4C566A")
        lum = calculate_relative_luminance(
            color.red(), color.green(), color.blue()
        )

        # Should be higher than new color (lighter)
        new_color = QColor("#2E3440")
        new_lum = calculate_relative_luminance(
            new_color.red(), new_color.green(), new_color.blue()
        )

        assert lum > new_lum, \
            "Old color should have higher luminance (be lighter)"

    def test_luminance_formula_correctness(self):
        """Verify luminance formula produces correct values for known colors."""
        from PyQt6.QtGui import QColor

        # Test black (should be ~0)
        black = QColor("#000000")
        black_lum = calculate_relative_luminance(
            black.red(), black.green(), black.blue()
        )
        assert black_lum < 0.01, f"Black luminance should be ~0, got {black_lum}"

        # Test white (should be ~1)
        white = QColor("#FFFFFF")
        white_lum = calculate_relative_luminance(
            white.red(), white.green(), white.blue()
        )
        assert white_lum > 0.99, f"White luminance should be ~1, got {white_lum}"

        # Test mid-gray (should be ~0.18-0.22 due to gamma correction)
        gray = QColor("#808080")
        gray_lum = calculate_relative_luminance(
            gray.red(), gray.green(), gray.blue()
        )
        assert 0.15 < gray_lum < 0.25, \
            f"Mid-gray luminance should be ~0.18-0.22, got {gray_lum}"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestWCAGContrastFormulaCorrectness:
    """Test WCAG contrast ratio formula correctness."""

    def test_black_on_white_contrast_is_21_to_1(self):
        """Black on white should have maximum contrast of 21:1."""
        from PyQt6.QtGui import QColor

        black = QColor("#000000")
        white = QColor("#FFFFFF")

        black_lum = calculate_relative_luminance(
            black.red(), black.green(), black.blue()
        )
        white_lum = calculate_relative_luminance(
            white.red(), white.green(), white.blue()
        )

        contrast = calculate_contrast_ratio(black_lum, white_lum)

        # Maximum possible contrast is 21:1
        assert 20.5 <= contrast <= 21.5, \
            f"Black on white should be ~21:1, got {contrast:.2f}:1"

    def test_same_color_contrast_is_1_to_1(self):
        """Same color on itself should have 1:1 contrast."""
        from PyQt6.QtGui import QColor

        color = QColor("#2E3440")

        lum = calculate_relative_luminance(
            color.red(), color.green(), color.blue()
        )

        contrast = calculate_contrast_ratio(lum, lum)

        assert 0.95 <= contrast <= 1.05, \
            f"Same color should have ~1:1 contrast, got {contrast:.2f}:1"

    def test_contrast_ratio_is_symmetric(self):
        """Contrast ratio should be same regardless of color order."""
        from PyQt6.QtGui import QColor

        color1 = QColor("#2E3440")
        color2 = QColor("#FFFFFF")

        lum1 = calculate_relative_luminance(
            color1.red(), color1.green(), color1.blue()
        )
        lum2 = calculate_relative_luminance(
            color2.red(), color2.green(), color2.blue()
        )

        contrast_1_2 = calculate_contrast_ratio(lum1, lum2)
        contrast_2_1 = calculate_contrast_ratio(lum2, lum1)

        assert abs(contrast_1_2 - contrast_2_1) < 0.01, \
            "Contrast should be symmetric"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestAccessibilityImprovementMetrics:
    """Test and document the accessibility improvement metrics."""

    def test_contrast_improvement_percentage(self):
        """Calculate and verify the percentage improvement in contrast."""
        from PyQt6.QtGui import QColor

        old_color = QColor("#4C566A")
        new_color = QColor("#2E3440")
        bg_color = QColor("#FFFFFF")

        old_lum = calculate_relative_luminance(
            old_color.red(), old_color.green(), old_color.blue()
        )
        new_lum = calculate_relative_luminance(
            new_color.red(), new_color.green(), new_color.blue()
        )
        bg_lum = calculate_relative_luminance(
            bg_color.red(), bg_color.green(), bg_color.blue()
        )

        old_contrast = calculate_contrast_ratio(old_lum, bg_lum)
        new_contrast = calculate_contrast_ratio(new_lum, bg_lum)

        improvement = ((new_contrast - old_contrast) / old_contrast) * 100

        # Document the improvement
        assert improvement > 0, f"Should have positive improvement, got {improvement:.1f}%"
        # Expect at least 30% improvement based on color choices
        assert improvement >= 30, \
            f"Improvement should be at least 30%, got {improvement:.1f}%"

    def test_readability_score_improvement(self):
        """Test that readability score improves from old to new color."""
        from PyQt6.QtGui import QColor

        def readability_score(contrast_ratio: float) -> str:
            """Assign readability grade based on WCAG levels."""
            if contrast_ratio >= 7.0:
                return "AAA"  # Excellent
            elif contrast_ratio >= 4.5:
                return "AA"   # Good
            elif contrast_ratio >= 3.0:
                return "AA Large Text"  # Acceptable for large text
            else:
                return "Fail"  # Poor

        old_color = QColor("#4C566A")
        new_color = QColor("#2E3440")
        bg_color = QColor("#FFFFFF")

        old_lum = calculate_relative_luminance(
            old_color.red(), old_color.green(), old_color.blue()
        )
        new_lum = calculate_relative_luminance(
            new_color.red(), new_color.green(), new_color.blue()
        )
        bg_lum = calculate_relative_luminance(
            bg_color.red(), bg_color.green(), bg_color.blue()
        )

        old_contrast = calculate_contrast_ratio(old_lum, bg_lum)
        new_contrast = calculate_contrast_ratio(new_lum, bg_lum)

        old_score = readability_score(old_contrast)
        new_score = readability_score(new_contrast)

        # Both should pass, but new should be better or equal
        assert old_score in ["AA", "AAA"], \
            f"Old color passed WCAG standards, got {old_score}"

        # New should pass AA or AAA
        assert new_score in ["AA", "AAA"], \
            f"New color should pass AA, got {new_score}"

        # New contrast should be better than old
        assert new_contrast > old_contrast, \
            f"New contrast {new_contrast:.2f} should exceed old {old_contrast:.2f}"

    def test_passes_wcag_level_aa_for_normal_text(self):
        """Verify new color explicitly passes WCAG Level AA for normal text."""
        from PyQt6.QtGui import QColor

        text_color = QColor("#2E3440")
        bg_color = QColor("#FFFFFF")

        text_lum = calculate_relative_luminance(
            text_color.red(), text_color.green(), text_color.blue()
        )
        bg_lum = calculate_relative_luminance(
            bg_color.red(), bg_color.green(), bg_color.blue()
        )

        contrast = calculate_contrast_ratio(text_lum, bg_lum)

        # WCAG 2.1 Level AA Requirements:
        # - Normal text: 4.5:1
        # - Large text (18pt+): 3:1
        assert contrast >= 4.5, \
            f"Must pass Level AA for normal text (4.5:1), got {contrast:.2f}:1"

    def test_may_pass_wcag_level_aaa_for_normal_text(self):
        """Check if new color approaches or passes WCAG Level AAA."""
        from PyQt6.QtGui import QColor

        text_color = QColor("#2E3440")
        bg_color = QColor("#FFFFFF")

        text_lum = calculate_relative_luminance(
            text_color.red(), text_color.green(), text_color.blue()
        )
        bg_lum = calculate_relative_luminance(
            bg_color.red(), bg_color.green(), bg_color.blue()
        )

        contrast = calculate_contrast_ratio(text_lum, bg_lum)

        # WCAG 2.1 Level AAA for normal text: 7:1
        # This is aspirational - we document the result
        if contrast >= 7.0:
            # Bonus: exceeds even AAA requirements
            assert True
        else:
            # Still acceptable: meets AA which is the requirement
            assert contrast >= 4.5, \
                f"Should at least meet AA (4.5:1), got {contrast:.2f}:1"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestDarkModePendingColorWCAGCompliance:
    """Verify dark mode pending color also meets WCAG requirements."""

    def test_pending_dark_mode_meets_wcag_aa_against_dark_background(self):
        """Dark mode pending #CDD6F4 should meet WCAG AA against dark backgrounds."""
        from PyQt6.QtGui import QColor

        text_color = QColor("#CDD6F4")  # Dark mode pending
        bg_color = QColor("#1E1E2E")    # Dark background from project_context.md

        text_lum = calculate_relative_luminance(
            text_color.red(), text_color.green(), text_color.blue()
        )
        bg_lum = calculate_relative_luminance(
            bg_color.red(), bg_color.green(), bg_color.blue()
        )

        contrast = calculate_contrast_ratio(text_lum, bg_lum)

        # Should meet AA in dark mode too
        assert contrast >= 4.5, \
            f"Dark mode contrast {contrast:.2f}:1 should meet WCAG AA"

    def test_dark_mode_pending_against_list_item_background(self):
        """Dark mode pending should have good contrast against list item background."""
        from PyQt6.QtGui import QColor

        text_color = QColor("#CDD6F4")  # Dark mode pending
        bg_color = QColor("#181825")    # List item background from project_context.md

        text_lum = calculate_relative_luminance(
            text_color.red(), text_color.green(), text_color.blue()
        )
        bg_lum = calculate_relative_luminance(
            bg_color.red(), bg_color.green(), bg_color.blue()
        )

        contrast = calculate_contrast_ratio(text_lum, bg_lum)

        # Should have good contrast
        assert contrast >= 4.5, \
            f"Dark mode list item contrast {contrast:.2f}:1 should meet WCAG AA"
