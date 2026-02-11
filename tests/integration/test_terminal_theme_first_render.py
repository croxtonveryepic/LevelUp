"""Integration tests for terminal theme initialization on first render.

These tests verify that terminals display the correct color scheme from the
very first render, without any visual flashing or color changes during
initialization. This ensures a seamless user experience when opening tickets
in the GUI.
"""

from __future__ import annotations

import pytest


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
class TestTerminalThemeFirstRender:
    """Test that terminal color scheme is correct from first render."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _ensure_qapp()

    def test_light_theme_terminal_correct_from_first_render(self):
        """When app starts in light mode, terminal should show light colors immediately."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Simulate app starting with light theme
            detail = TicketDetailWidget()
            detail._current_theme = "light"

            # Create first terminal
            detail.set_ticket(_make_ticket(1))

            # Terminal should have light colors from the start
            terminal = detail._terminals[1]
            assert terminal._terminal._color_scheme == LightTerminalColors

            # Verify no additional set_color_scheme calls would be needed
            # (the color scheme is already correct)
            expected_scheme = LightTerminalColors
            actual_scheme = terminal._terminal._color_scheme
            assert actual_scheme == expected_scheme

    def test_dark_theme_terminal_correct_from_first_render(self):
        """When app starts in dark mode, terminal should show dark colors immediately."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import CatppuccinMochaColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Simulate app starting with dark theme
            detail = TicketDetailWidget()
            detail._current_theme = "dark"

            # Create first terminal
            detail.set_ticket(_make_ticket(1))

            # Terminal should have dark colors from the start
            terminal = detail._terminals[1]
            assert terminal._terminal._color_scheme == CatppuccinMochaColors

            # Verify no additional set_color_scheme calls would be needed
            expected_scheme = CatppuccinMochaColors
            actual_scheme = terminal._terminal._color_scheme
            assert actual_scheme == expected_scheme

    def test_system_theme_light_terminal_correct_from_first_render(self):
        """When system theme is light, terminal should show light colors immediately."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Simulate system theme resolving to light
            detail = TicketDetailWidget()
            # MainWindow sets _current_theme = get_current_theme()
            # which resolves "system" to actual theme
            detail._current_theme = "light"

            # Create terminal
            detail.set_ticket(_make_ticket(1))

            # Should be light from first render
            terminal = detail._terminals[1]
            assert terminal._terminal._color_scheme == LightTerminalColors

    def test_system_theme_dark_terminal_correct_from_first_render(self):
        """When system theme is dark, terminal should show dark colors immediately."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import CatppuccinMochaColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Simulate system theme resolving to dark
            detail = TicketDetailWidget()
            detail._current_theme = "dark"

            # Create terminal
            detail.set_ticket(_make_ticket(1))

            # Should be dark from first render
            terminal = detail._terminals[1]
            assert terminal._terminal._color_scheme == CatppuccinMochaColors

    def test_no_color_scheme_change_after_first_render_light(self):
        """Terminal created in light theme should not need color scheme change."""
        from unittest.mock import patch, MagicMock
        from levelup.gui.ticket_detail import TicketDetailWidget

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            detail = TicketDetailWidget()
            detail._current_theme = "light"

            # Create terminal
            detail.set_ticket(_make_ticket(1))
            terminal = detail._terminals[1]

            # Mock set_color_scheme to track post-creation calls
            original_set_color_scheme = terminal._terminal.set_color_scheme
            terminal._terminal.set_color_scheme = MagicMock(side_effect=original_set_color_scheme)

            # Simulate a render cycle (show event, paint event, etc.)
            terminal.show()
            terminal._terminal.show()

            # No set_color_scheme should have been called after construction
            terminal._terminal.set_color_scheme.assert_not_called()

    def test_no_color_scheme_change_after_first_render_dark(self):
        """Terminal created in dark theme should not need color scheme change."""
        from unittest.mock import patch, MagicMock
        from levelup.gui.ticket_detail import TicketDetailWidget

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            detail = TicketDetailWidget()
            detail._current_theme = "dark"

            # Create terminal
            detail.set_ticket(_make_ticket(1))
            terminal = detail._terminals[1]

            # Mock set_color_scheme to track post-creation calls
            original_set_color_scheme = terminal._terminal.set_color_scheme
            terminal._terminal.set_color_scheme = MagicMock(side_effect=original_set_color_scheme)

            # Simulate a render cycle
            terminal.show()
            terminal._terminal.show()

            # No set_color_scheme should have been called after construction
            terminal._terminal.set_color_scheme.assert_not_called()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestNoVisualFlashingOnTerminalCreation:
    """Test that there is no visual flashing when creating terminals."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _ensure_qapp()

    def test_single_color_scheme_assignment_during_construction(self):
        """Color scheme should be set exactly once during construction, not changed later."""
        from unittest.mock import patch, MagicMock
        from levelup.gui.ticket_detail import TicketDetailWidget

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            detail = TicketDetailWidget()
            detail._current_theme = "light"

            # Track TerminalEmulatorWidget construction
            with patch("levelup.gui.run_terminal.TerminalEmulatorWidget") as MockEmulator:
                mock_terminal = MagicMock()
                MockEmulator.return_value = mock_terminal

                terminal = detail._get_or_create_terminal(1)

                # Should be constructed with color_scheme parameter
                MockEmulator.assert_called_once()
                call_kwargs = MockEmulator.call_args[1] if MockEmulator.call_args else {}
                assert 'color_scheme' in call_kwargs

                # set_color_scheme should not be called on the mock
                mock_terminal.set_color_scheme.assert_not_called()

    def test_color_scheme_consistent_throughout_initialization(self):
        """Color scheme should remain consistent throughout widget initialization."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            detail = TicketDetailWidget()
            detail._current_theme = "light"

            # Create terminal
            terminal = detail._get_or_create_terminal(1)

            # Check color scheme immediately after creation
            initial_scheme = terminal._terminal._color_scheme
            assert initial_scheme == LightTerminalColors

            # Simulate various initialization steps
            terminal.set_context("/project", "/db.db")
            terminal.enable_run(True)

            # Color scheme should not have changed
            final_scheme = terminal._terminal._color_scheme
            assert final_scheme == LightTerminalColors
            assert final_scheme is initial_scheme

    def test_multiple_terminals_created_sequentially_all_correct(self):
        """When creating multiple terminals in sequence, all should have correct theme."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            detail = TicketDetailWidget()
            detail._current_theme = "light"

            # Create several terminals
            for i in range(1, 6):
                detail.set_ticket(_make_ticket(i))
                terminal = detail._terminals[i]

                # Each should have light theme from creation
                assert terminal._terminal._color_scheme == LightTerminalColors

    def test_terminals_in_different_themes_each_correct(self):
        """Terminals created under different themes should each be correct."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors, CatppuccinMochaColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            detail = TicketDetailWidget()

            # Create terminal in light mode
            detail._current_theme = "light"
            detail.set_ticket(_make_ticket(1))
            terminal_light = detail._terminals[1]
            assert terminal_light._terminal._color_scheme == LightTerminalColors

            # Switch to dark mode and create another terminal
            detail._current_theme = "dark"
            detail.set_ticket(_make_ticket(2))
            terminal_dark = detail._terminals[2]
            assert terminal_dark._terminal._color_scheme == CatppuccinMochaColors

            # Both should retain their correct color schemes
            assert terminal_light._terminal._color_scheme == LightTerminalColors
            assert terminal_dark._terminal._color_scheme == CatppuccinMochaColors


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestBackwardCompatibilityAfterThemeParameter:
    """Test backward compatibility after adding theme parameter."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _ensure_qapp()

    def test_existing_code_without_theme_parameter_still_works(self):
        """Code that creates RunTerminalWidget() without theme should still work."""
        from unittest.mock import patch
        from levelup.gui.run_terminal import RunTerminalWidget

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Old code that doesn't pass theme parameter
            widget = RunTerminalWidget()

            # Should work without error
            assert widget is not None
            assert widget._terminal is not None

            widget.deleteLater()

    def test_ticket_detail_without_explicit_theme_attribute_uses_default(self):
        """TicketDetailWidget without _current_theme attribute should use default."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import CatppuccinMochaColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            detail = TicketDetailWidget()

            # Don't set _current_theme (simulate old code path)
            if hasattr(detail, '_current_theme'):
                delattr(detail, '_current_theme')

            # Create terminal - should use default dark
            terminal = detail._get_or_create_terminal(1)
            assert terminal._terminal._color_scheme == CatppuccinMochaColors

    def test_manual_set_color_scheme_still_works_for_dynamic_switching(self):
        """Manual set_color_scheme should still work for theme switching after creation."""
        from unittest.mock import patch
        from levelup.gui.run_terminal import RunTerminalWidget
        from levelup.gui.terminal_emulator import LightTerminalColors, CatppuccinMochaColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Create with dark theme
            widget = RunTerminalWidget(theme="dark")
            assert widget._terminal._color_scheme == CatppuccinMochaColors

            # Manually switch to light (for dynamic theme changes)
            widget._terminal.set_color_scheme(LightTerminalColors)
            assert widget._terminal._color_scheme == LightTerminalColors

            widget.deleteLater()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestEndToEndThemeInitialization:
    """End-to-end tests for complete theme initialization flow."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _ensure_qapp()

    def test_complete_flow_app_starts_light_terminal_created_light(self):
        """Complete flow: app starts in light mode, user opens ticket, terminal is light."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Step 1: App starts with light theme
            # (MainWindow would call apply_theme(app, "light"))

            # Step 2: TicketDetailWidget is created with light theme
            detail = TicketDetailWidget()
            detail._current_theme = "light"

            # Step 3: User clicks on a ticket
            detail.set_ticket(_make_ticket(1))

            # Step 4: Terminal is created
            terminal = detail._terminals[1]

            # Verify: Terminal has light colors from first render
            assert terminal._terminal._color_scheme == LightTerminalColors

    def test_complete_flow_app_starts_dark_terminal_created_dark(self):
        """Complete flow: app starts in dark mode, user opens ticket, terminal is dark."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import CatppuccinMochaColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Step 1: App starts with dark theme

            # Step 2: TicketDetailWidget is created with dark theme
            detail = TicketDetailWidget()
            detail._current_theme = "dark"

            # Step 3: User clicks on a ticket
            detail.set_ticket(_make_ticket(1))

            # Step 4: Terminal is created
            terminal = detail._terminals[1]

            # Verify: Terminal has dark colors from first render
            assert terminal._terminal._color_scheme == CatppuccinMochaColors

    def test_complete_flow_user_switches_theme_then_creates_terminal(self):
        """Complete flow: user switches theme, then opens ticket, terminal matches new theme."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors, CatppuccinMochaColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Start with dark theme
            detail = TicketDetailWidget()
            detail._current_theme = "dark"

            # User switches to light theme
            detail._current_theme = "light"
            detail.update_theme("light")

            # User opens a ticket
            detail.set_ticket(_make_ticket(1))

            # Terminal should be light (matching current theme)
            terminal = detail._terminals[1]
            assert terminal._terminal._color_scheme == LightTerminalColors

    def test_complete_flow_terminal_exists_then_theme_switches(self):
        """Complete flow: terminal exists, user switches theme, terminal updates."""
        from unittest.mock import patch
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.gui.terminal_emulator import LightTerminalColors, CatppuccinMochaColors

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            # Start with dark theme
            detail = TicketDetailWidget()
            detail._current_theme = "dark"

            # Create terminal
            detail.set_ticket(_make_ticket(1))
            terminal = detail._terminals[1]
            assert terminal._terminal._color_scheme == CatppuccinMochaColors

            # User switches to light theme
            detail._current_theme = "light"
            detail.update_theme("light")

            # Terminal should update to light
            assert terminal._terminal._color_scheme == LightTerminalColors
