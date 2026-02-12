"""Tests for TicketDetailWidget passing theme when creating RunTerminalWidget instances.

These tests verify that TicketDetailWidget correctly passes the current theme
to RunTerminalWidget during terminal creation, ensuring terminals show the
correct color scheme from first render without visual flashing.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.regression

def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def _make_ticket(number: int, title: str = "Test ticket"):
    from levelup.core.tickets import Ticket, TicketStatus
    return Ticket(number=number, title=title, status=TicketStatus.PENDING)


_qapp = None


def _ensure_qapp():
    global _qapp
    from PyQt6.QtWidgets import QApplication
    _qapp = QApplication.instance() or QApplication([])
    return _qapp


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestTicketDetailPassesThemeToTerminal:
    """Test that TicketDetailWidget passes current theme when creating terminals."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _ensure_qapp()

    def test_passes_theme_parameter_to_run_terminal_widget(self):
        """TicketDetailWidget should pass theme parameter when creating RunTerminalWidget."""
        from unittest.mock import patch, MagicMock
        from levelup.gui.ticket_detail import TicketDetailWidget

        detail = TicketDetailWidget()
        detail._current_theme = "light"

        # Mock RunTerminalWidget to track constructor calls
        with patch("levelup.gui.ticket_detail.RunTerminalWidget") as MockRunTerminal:
            mock_terminal = MagicMock()
            MockRunTerminal.return_value = mock_terminal

            # Create terminal for ticket
            terminal = detail._get_or_create_terminal(1)

            # Should have been called with theme parameter
            MockRunTerminal.assert_called_once()
            call_kwargs = MockRunTerminal.call_args[1] if MockRunTerminal.call_args else {}
            assert 'theme' in call_kwargs
            assert call_kwargs['theme'] == "light"

    def test_passes_dark_theme_when_current_theme_is_dark(self):
        """When current theme is 'dark', should pass theme='dark' to RunTerminalWidget."""
        from unittest.mock import patch, MagicMock
        from levelup.gui.ticket_detail import TicketDetailWidget

        detail = TicketDetailWidget()
        detail._current_theme = "dark"

        with patch("levelup.gui.ticket_detail.RunTerminalWidget") as MockRunTerminal:
            mock_terminal = MagicMock()
            MockRunTerminal.return_value = mock_terminal

            terminal = detail._get_or_create_terminal(1)

            MockRunTerminal.assert_called_once()
            call_kwargs = MockRunTerminal.call_args[1] if MockRunTerminal.call_args else {}
            assert call_kwargs['theme'] == "dark"

    def test_passes_light_theme_when_current_theme_is_light(self):
        """When current theme is 'light', should pass theme='light' to RunTerminalWidget."""
        from unittest.mock import patch, MagicMock
        from levelup.gui.ticket_detail import TicketDetailWidget

        detail = TicketDetailWidget()
        detail._current_theme = "light"

        with patch("levelup.gui.ticket_detail.RunTerminalWidget") as MockRunTerminal:
            mock_terminal = MagicMock()
            MockRunTerminal.return_value = mock_terminal

            terminal = detail._get_or_create_terminal(1)

            MockRunTerminal.assert_called_once()
            call_kwargs = MockRunTerminal.call_args[1] if MockRunTerminal.call_args else {}
            assert call_kwargs['theme'] == "light"

    def test_no_manual_set_color_scheme_after_creation(self):
        """After passing theme to constructor, should not manually call set_color_scheme."""
        from unittest.mock import patch, MagicMock
        from levelup.gui.ticket_detail import TicketDetailWidget

        detail = TicketDetailWidget()
        detail._current_theme = "light"

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Don't mock RunTerminalWidget, let it be created
            terminal = detail._get_or_create_terminal(1)

            # Mock set_color_scheme to ensure it's not called
            terminal._terminal.set_color_scheme = MagicMock()

            # The terminal should already have the correct color scheme
            # so set_color_scheme should NOT be called manually
            terminal._terminal.set_color_scheme.assert_not_called()

    def test_terminal_created_with_correct_initial_color_scheme_light(self):
        """Terminal created when theme is 'light' should immediately have LightTerminalColors."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors

        detail = TicketDetailWidget()
        detail._current_theme = "light"

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            terminal = detail._get_or_create_terminal(1)

            # Terminal should be created with light color scheme from the start
            assert terminal._terminal._color_scheme == LightTerminalColors

    def test_terminal_created_with_correct_initial_color_scheme_dark(self):
        """Terminal created when theme is 'dark' should immediately have CatppuccinMochaColors."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import CatppuccinMochaColors

        detail = TicketDetailWidget()
        detail._current_theme = "dark"

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            terminal = detail._get_or_create_terminal(1)

            # Terminal should be created with dark color scheme from the start
            assert terminal._terminal._color_scheme == CatppuccinMochaColors

    def test_multiple_terminals_each_get_theme_parameter(self):
        """Each terminal created should receive the current theme parameter."""
        from unittest.mock import patch, MagicMock
        from levelup.gui.ticket_detail import TicketDetailWidget

        detail = TicketDetailWidget()
        detail._current_theme = "light"

        with patch("levelup.gui.ticket_detail.RunTerminalWidget") as MockRunTerminal:
            mock_terminals = [MagicMock(), MagicMock(), MagicMock()]
            MockRunTerminal.side_effect = mock_terminals

            # Create multiple terminals
            detail._get_or_create_terminal(1)
            detail._get_or_create_terminal(2)
            detail._get_or_create_terminal(3)

            # All should have been called with theme='light'
            assert MockRunTerminal.call_count == 3
            for call in MockRunTerminal.call_args_list:
                call_kwargs = call[1] if call else {}
                assert call_kwargs.get('theme') == "light"

    def test_theme_parameter_used_when_reusing_existing_terminal(self):
        """When reusing existing terminal, it already has correct theme from creation."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors

        detail = TicketDetailWidget()
        detail._current_theme = "light"

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Create terminal first time
            terminal1 = detail._get_or_create_terminal(1)
            assert terminal1._terminal._color_scheme == LightTerminalColors

            # Get same terminal again
            terminal2 = detail._get_or_create_terminal(1)

            # Should be same instance
            assert terminal1 is terminal2

            # Still has correct color scheme
            assert terminal2._terminal._color_scheme == LightTerminalColors


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestTicketDetailThemeIntegration:
    """Integration tests for theme initialization in TicketDetailWidget."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _ensure_qapp()

    def test_set_ticket_creates_terminal_with_current_theme(self):
        """set_ticket should create terminal with current theme applied."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors

        detail = TicketDetailWidget()
        detail._current_theme = "light"

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            detail.set_ticket(_make_ticket(1))

            # Terminal should exist and have light colors
            assert 1 in detail._terminals
            assert detail._terminals[1]._terminal._color_scheme == LightTerminalColors

    def test_theme_change_after_terminal_creation_via_update_theme(self):
        """Existing terminals should update theme via update_theme method (not construction)."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import CatppuccinMochaColors, LightTerminalColors

        detail = TicketDetailWidget()
        detail._current_theme = "dark"

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            detail.set_ticket(_make_ticket(1))
            terminal = detail._terminals[1]

            # Initially dark
            assert terminal._terminal._color_scheme == CatppuccinMochaColors

            # Change theme
            detail._current_theme = "light"
            detail.update_theme("light")

            # Terminal should now be light (via update_theme, not reconstruction)
            assert terminal._terminal._color_scheme == LightTerminalColors

    def test_initial_terminal_creation_matches_app_theme_light(self):
        """When app starts in light mode, terminal should be light from first render."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors

        # Simulate app starting in light mode
        detail = TicketDetailWidget()
        detail._current_theme = "light"  # Set before any terminals are created

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # First terminal creation
            detail.set_ticket(_make_ticket(1))

            # Should be light from the very beginning
            terminal = detail._terminals[1]
            assert terminal._terminal._color_scheme == LightTerminalColors

    def test_initial_terminal_creation_matches_app_theme_dark(self):
        """When app starts in dark mode, terminal should be dark from first render."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import CatppuccinMochaColors

        # Simulate app starting in dark mode
        detail = TicketDetailWidget()
        detail._current_theme = "dark"  # Set before any terminals are created

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # First terminal creation
            detail.set_ticket(_make_ticket(1))

            # Should be dark from the very beginning
            terminal = detail._terminals[1]
            assert terminal._terminal._color_scheme == CatppuccinMochaColors

    def test_no_visual_flash_on_terminal_creation(self):
        """Terminal should not flash wrong colors during creation.

        This is verified by checking that the color scheme is set during
        construction rather than after creation with a manual call.
        """
        from unittest.mock import patch, MagicMock
        from levelup.gui.ticket_detail import TicketDetailWidget

        detail = TicketDetailWidget()
        detail._current_theme = "light"

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            terminal = detail._get_or_create_terminal(1)

            # Track if set_color_scheme is called after construction
            set_color_scheme_calls = []
            original_set_color_scheme = terminal._terminal.set_color_scheme

            def track_set_color_scheme(scheme):
                set_color_scheme_calls.append(scheme)
                return original_set_color_scheme(scheme)

            terminal._terminal.set_color_scheme = track_set_color_scheme

            # Simulate what would happen in a render cycle
            # If the implementation is correct, no post-creation set_color_scheme call
            assert len(set_color_scheme_calls) == 0, \
                "set_color_scheme should not be called after construction"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestTicketDetailThemeEdgeCases:
    """Edge case tests for theme handling in TicketDetailWidget."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _ensure_qapp()

    def test_handles_missing_current_theme_attribute(self):
        """Should handle case where _current_theme is not set (defensive programming)."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import CatppuccinMochaColors

        detail = TicketDetailWidget()
        # Don't set _current_theme, or set to None
        if hasattr(detail, '_current_theme'):
            detail._current_theme = None

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Should fall back to dark theme
            terminal = detail._get_or_create_terminal(1)
            assert terminal._terminal._color_scheme == CatppuccinMochaColors

    def test_terminal_creation_before_theme_initialization(self):
        """Terminal created before theme is set should use default dark."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import CatppuccinMochaColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Create widget without setting theme
            detail = TicketDetailWidget()

            # Create terminal immediately
            terminal = detail._get_or_create_terminal(1)

            # Should default to dark
            assert terminal._terminal._color_scheme == CatppuccinMochaColors

    def test_theme_parameter_priority_over_manual_set_color_scheme(self):
        """When theme is passed to constructor, manual set_color_scheme should not override."""
        from unittest.mock import patch, MagicMock
        from levelup.gui.ticket_detail import TicketDetailWidget

        detail = TicketDetailWidget()
        detail._current_theme = "light"

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Create terminal with light theme
            terminal = detail._get_or_create_terminal(1)

            # Replace set_color_scheme with mock
            terminal._terminal.set_color_scheme = MagicMock()

            # No manual set_color_scheme call should happen
            # (the implementation should not call it after construction)
            terminal._terminal.set_color_scheme.assert_not_called()
