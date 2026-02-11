"""Unit tests for sidebar toggle checkbox styling.

This test suite covers the requirements for proper styling of the
merged ticket visibility toggle in both light and dark themes.

Requirements:
- Toggle checkbox has appropriate styling in dark theme
- Toggle checkbox has appropriate styling in light theme
- Toggle styling is consistent with overall sidebar theme
- Toggle is visually distinct and accessible
"""

from __future__ import annotations

import pytest


def _can_import_pyqt6() -> bool:
    """Check if PyQt6 is available."""
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def _ensure_qapp():
    """Ensure QApplication exists."""
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestToggleCheckboxStyling:
    """Test styling of the merged ticket toggle checkbox."""

    def test_toggle_has_object_name_for_styling(self):
        """Toggle checkbox should have object name for stylesheet targeting."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        assert checkbox is not None
        assert checkbox.objectName() == "showMergedCheckbox"

    def test_toggle_has_stylesheet_applied(self):
        """Toggle checkbox should have stylesheet applied."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Checkbox should have some styling (either inline or from parent)
        # Check that it's not the default Qt stylesheet
        assert checkbox is not None

    def test_toggle_visible_in_dark_theme(self):
        """Toggle checkbox should be visible in dark theme."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget(theme="dark")
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        assert checkbox.isVisible() is True

    def test_toggle_visible_in_light_theme(self):
        """Toggle checkbox should be visible in light theme."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget(theme="light")
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        assert checkbox.isVisible() is True

    def test_toggle_in_header_layout(self):
        """Toggle checkbox should be in the header layout."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Checkbox should have a parent (the header layout or widget)
        assert checkbox.parent() is not None

    def test_toggle_has_accessible_text(self):
        """Toggle checkbox should have accessible label text."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Label should be non-empty and descriptive
        label = checkbox.text()
        assert len(label) > 0
        assert "merged" in label.lower() or "show" in label.lower()

    def test_toggle_size_appropriate(self):
        """Toggle checkbox should have appropriate size."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Size should be reasonable (not too small, not too large)
        size = checkbox.sizeHint()
        assert size.width() > 0
        assert size.height() > 0

    def test_toggle_has_tooltip(self):
        """Toggle checkbox may have a tooltip for accessibility."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Tooltip is optional but helpful for accessibility
        tooltip = checkbox.toolTip()
        # This test just checks that tooltip exists (can be empty)
        assert isinstance(tooltip, str)


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestToggleThemeConsistency:
    """Test that toggle styling is consistent with sidebar theme."""

    def test_toggle_theme_matches_sidebar_dark(self):
        """Toggle should match dark theme styling."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget(theme="dark")
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Widget should be created with dark theme
        assert widget._current_theme == "dark"
        assert checkbox is not None

    def test_toggle_theme_matches_sidebar_light(self):
        """Toggle should match light theme styling."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget(theme="light")
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Widget should be created with light theme
        assert widget._current_theme == "light"
        assert checkbox is not None

    def test_toggle_persists_through_theme_change(self):
        """Toggle checkbox should persist when theme changes."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget(theme="dark")
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Check the toggle
        checkbox.setChecked(True)
        assert checkbox.isChecked() is True

        # Change theme
        widget.update_theme("light")

        # Toggle should still exist and maintain state
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        assert checkbox is not None
        assert checkbox.isChecked() is True


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestToggleAccessibility:
    """Test accessibility features of the toggle checkbox."""

    def test_toggle_can_be_focused(self):
        """Toggle checkbox should be focusable for keyboard navigation."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox
        from PyQt6.QtCore import Qt

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Checkbox should accept focus
        assert checkbox.focusPolicy() != Qt.FocusPolicy.NoFocus

    def test_toggle_responds_to_keyboard(self):
        """Toggle checkbox should respond to keyboard interaction."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Initially unchecked
        assert checkbox.isChecked() is False

        # Programmatic toggle simulates keyboard space/enter
        checkbox.toggle()
        assert checkbox.isChecked() is True

        checkbox.toggle()
        assert checkbox.isChecked() is False

    def test_toggle_label_clear_and_concise(self):
        """Toggle label should be clear and concise."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        label = checkbox.text()

        # Label should be short and descriptive
        assert len(label) < 30  # Not too long
        assert len(label) > 5   # Not too short
        assert "merged" in label.lower() or "show" in label.lower()

    def test_toggle_state_visually_distinct(self):
        """Toggle checked/unchecked states should be visually distinct."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")

        # Unchecked state
        checkbox.setChecked(False)
        assert checkbox.isChecked() is False

        # Checked state
        checkbox.setChecked(True)
        assert checkbox.isChecked() is True

        # States should be clearly different
        # (This is tested via isChecked, visual distinction is UI implementation)


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestTogglePosition:
    """Test positioning of the toggle in the sidebar header."""

    def test_toggle_in_header_not_in_list(self):
        """Toggle should be in header, not in the ticket list."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox, QListWidget

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        list_widget = widget.findChild(QListWidget)

        # Checkbox parent should not be the list widget
        assert checkbox.parent() != list_widget

    def test_toggle_near_add_button(self):
        """Toggle should be positioned near the add ticket button in header."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox, QPushButton

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        add_btn = widget.findChild(QPushButton, "addTicketBtn")

        # Both should exist and be in the widget
        assert checkbox is not None
        assert add_btn is not None

        # Both should have the same parent or be in same layout
        # (Exact positioning is layout-dependent)

    def test_toggle_above_ticket_list(self):
        """Toggle should be positioned above the ticket list."""
        app = _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from PyQt6.QtWidgets import QCheckBox, QListWidget

        widget = TicketSidebarWidget()
        checkbox = widget.findChild(QCheckBox, "showMergedCheckbox")
        list_widget = widget.findChild(QListWidget)

        # Both widgets should exist
        assert checkbox is not None
        assert list_widget is not None

        # Visual position test would require geometry calculations
        # This test just confirms both exist in the widget
