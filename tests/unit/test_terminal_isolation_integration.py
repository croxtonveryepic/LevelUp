"""Integration tests verifying that terminal isolation works with delayed initialization.

This module tests that the delayed initialization changes do not break the existing
terminal isolation behavior where each ticket gets its own independent terminal instance.
"""

from __future__ import annotations

from unittest.mock import patch

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


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestTerminalIsolationWithDelayedInit:
    """Verify terminal isolation works correctly with delayed initialization."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Setup QApplication for PyQt6 tests."""
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_detail(self):
        """Create a TicketDetailWidget with mocked PTY backend."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.ticket_detail import TicketDetailWidget
            widget = TicketDetailWidget()
        return widget

    # -------------------------------------------------------------------------
    # Test: Terminal instances remain isolated per ticket
    # -------------------------------------------------------------------------

    def test_different_tickets_have_separate_terminals(self):
        """Verify each ticket gets its own terminal instance."""
        detail = self._make_detail()
        detail.set_project_context("/test/project", "/test/db.db")

        # Select ticket 1
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal
        assert term1 is not None
        assert term1._ticket_number == 1

        # Select ticket 2
        detail.set_ticket(_make_ticket(2))
        term2 = detail._current_terminal
        assert term2 is not None
        assert term2._ticket_number == 2

        # Terminals should be different instances
        assert term1 is not term2
        assert 1 in detail._terminals
        assert 2 in detail._terminals

    def test_ticket_terminals_have_independent_shell_state(self):
        """Verify each ticket's terminal has independent _shell_started state."""
        detail = self._make_detail()
        detail.set_project_context("/test/project", "/test/db.db")

        # Create terminals for two tickets
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal
        detail.set_ticket(_make_ticket(2))
        term2 = detail._current_terminal

        # Neither should have shell started yet
        assert term1._shell_started is False
        assert term2._shell_started is False

        # Start shell for ticket 1
        with patch.object(term1._terminal, "start_shell"), \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1.start_run(ticket_number=1, project_path="/p", db_path="/d")

        # Only term1 should have shell started
        assert term1._shell_started is True
        assert term2._shell_started is False

    def test_switching_tickets_preserves_terminal_state(self):
        """Verify switching between tickets preserves each terminal's state."""
        detail = self._make_detail()
        detail.set_project_context("/test/project", "/test/db.db")

        # Create and start run on ticket 1
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal

        with patch.object(term1._terminal, "start_shell"), \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1.start_run(ticket_number=1, project_path="/p", db_path="/d")
        assert term1._shell_started is True
        assert term1._command_running is True

        # Switch to ticket 2 (no run)
        detail.set_ticket(_make_ticket(2))
        term2 = detail._current_terminal
        assert term2._shell_started is False
        assert term2._command_running is False

        # Switch back to ticket 1
        detail.set_ticket(_make_ticket(1))
        assert detail._current_terminal is term1
        # State should be preserved
        assert term1._shell_started is True
        assert term1._command_running is True

    def test_viewing_ticket_does_not_affect_other_terminals(self):
        """Verify that viewing a ticket doesn't trigger shell init in other terminals."""
        detail = self._make_detail()
        detail.set_project_context("/test/project", "/test/db.db")

        # Create terminal for ticket 1 and start shell
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal

        with patch.object(term1._terminal, "start_shell") as mock_start1, \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert mock_start1.call_count == 1

        # Now create and view ticket 2 (should not start shell)
        detail.set_ticket(_make_ticket(2))
        term2 = detail._current_terminal

        with patch.object(term2._terminal, "start_shell") as mock_start2:
            # Show term2 (trigger showEvent)
            from PyQt6.QtGui import QShowEvent
            event = QShowEvent()
            term2.showEvent(event)

            # Should NOT start shell
            mock_start2.assert_not_called()
            assert term2._shell_started is False

        # Term1 should still be in running state
        assert term1._shell_started is True

    def test_multiple_tickets_can_run_independently(self):
        """Verify multiple tickets can each have their own active run."""
        detail = self._make_detail()
        detail.set_project_context("/test/project", "/test/db.db")

        # Start run on ticket 1
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal
        with patch.object(term1._terminal, "start_shell"), \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1.start_run(ticket_number=1, project_path="/p", db_path="/d")

        # Start run on ticket 2
        detail.set_ticket(_make_ticket(2))
        term2 = detail._current_terminal
        with patch.object(term2._terminal, "start_shell"), \
             patch.object(term2._terminal, "send_command"), \
             patch.object(term2._terminal, "setFocus"):
            term2.start_run(ticket_number=2, project_path="/p", db_path="/d")

        # Both should be in running state with shells started
        assert term1._shell_started is True
        assert term1._command_running is True
        assert term2._shell_started is True
        assert term2._command_running is True

    # -------------------------------------------------------------------------
    # Test: Terminal cleanup still works correctly
    # -------------------------------------------------------------------------

    def test_cleanup_closes_only_started_shells(self):
        """Verify cleanup only attempts to close shells that were actually started."""
        detail = self._make_detail()
        detail.set_project_context("/test/project", "/test/db.db")

        # Create 3 terminals
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal
        detail.set_ticket(_make_ticket(2))
        term2 = detail._current_terminal
        detail.set_ticket(_make_ticket(3))
        term3 = detail._current_terminal

        # Start shell only on term1 and term3
        with patch.object(term1._terminal, "start_shell"), \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1.start_run(ticket_number=1, project_path="/p", db_path="/d")

        with patch.object(term3._terminal, "start_shell"), \
             patch.object(term3._terminal, "send_command"), \
             patch.object(term3._terminal, "setFocus"):
            term3.start_run(ticket_number=3, project_path="/p", db_path="/d")

        # Mock close_shell for all terminals
        with patch.object(term1._terminal, "close_shell") as mock_close1, \
             patch.object(term2._terminal, "close_shell") as mock_close2, \
             patch.object(term3._terminal, "close_shell") as mock_close3:

            # Clean up all terminals
            detail.cleanup_all_terminals()

            # Only term1 and term3 should have close_shell called
            assert mock_close1.call_count == 1
            mock_close2.assert_not_called()  # Shell never started
            assert mock_close3.call_count == 1

    def test_remove_terminal_only_closes_started_shell(self):
        """Verify removing a terminal only closes shell if it was started."""
        detail = self._make_detail()
        detail.set_project_context("/test/project", "/test/db.db")

        # Create terminal without starting shell
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal
        assert term1._shell_started is False

        # Remove it
        with patch.object(term1._terminal, "close_shell") as mock_close:
            detail._remove_terminal(1)
            # close_shell should not be called since shell never started
            mock_close.assert_not_called()

    def test_remove_terminal_closes_started_shell(self):
        """Verify removing a terminal closes shell if it was started."""
        detail = self._make_detail()
        detail.set_project_context("/test/project", "/test/db.db")

        # Create terminal and start shell
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal

        with patch.object(term1._terminal, "start_shell"), \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1.start_run(ticket_number=1, project_path="/p", db_path="/d")
        assert term1._shell_started is True

        # Remove it
        with patch.object(term1._terminal, "close_shell") as mock_close:
            detail._remove_terminal(1)
            # close_shell SHOULD be called since shell was started
            mock_close.assert_called_once()

    # -------------------------------------------------------------------------
    # Test: Terminal reuse works with delayed initialization
    # -------------------------------------------------------------------------

    def test_reusing_terminal_preserves_shell_state(self):
        """Verify that reusing a terminal (switching back) preserves shell state."""
        detail = self._make_detail()
        detail.set_project_context("/test/project", "/test/db.db")

        # Create terminal for ticket 1
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal

        # Start a run
        with patch.object(term1._terminal, "start_shell"), \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1.start_run(ticket_number=1, project_path="/p", db_path="/d")
        assert term1._shell_started is True

        # Finish the run
        term1._command_running = False

        # Switch to ticket 2
        detail.set_ticket(_make_ticket(2))
        term2 = detail._current_terminal

        # Switch back to ticket 1
        detail.set_ticket(_make_ticket(1))
        term1_again = detail._current_terminal

        # Should be the same instance
        assert term1_again is term1
        # Shell should still be marked as started
        assert term1_again._shell_started is True

        # Starting another run should NOT start shell again
        with patch.object(term1._terminal, "start_shell") as mock_start, \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1_again.start_run(ticket_number=1, project_path="/p", db_path="/d")
            # Shell should not be started again
            mock_start.assert_not_called()

    def test_terminal_reuse_after_shell_exit(self):
        """Verify terminal can be reused after shell exits."""
        detail = self._make_detail()
        detail.set_project_context("/test/project", "/test/db.db")

        # Create terminal and start run
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal

        with patch.object(term1._terminal, "start_shell"), \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1.start_run(ticket_number=1, project_path="/p", db_path="/d")
        assert term1._shell_started is True

        # Shell exits
        term1._on_shell_exited(0)
        assert term1._shell_started is False

        # Start another run (should start shell again)
        with patch.object(term1._terminal, "start_shell") as mock_start, \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1.start_run(ticket_number=1, project_path="/p", db_path="/d")
            # Shell should be started again
            mock_start.assert_called_once()
            assert term1._shell_started is True

    # -------------------------------------------------------------------------
    # Test: Context propagation works with delayed init
    # -------------------------------------------------------------------------

    def test_context_propagated_before_shell_start(self):
        """Verify project context is available when shell starts."""
        detail = self._make_detail()

        # Set context BEFORE creating terminals
        detail.set_project_context("/my/project", "/my/db.db")

        # Create terminal
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal

        # Verify context was propagated
        assert term1._project_path == "/my/project"
        assert term1._db_path == "/my/db.db"

        # Start run and verify cwd is passed correctly
        with patch.object(term1._terminal, "start_shell") as mock_start, \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1.start_run(ticket_number=1, project_path="/my/project", db_path="/my/db.db")

            # Verify start_shell was called with correct cwd
            mock_start.assert_called_once()
            call_kwargs = mock_start.call_args[1]
            assert call_kwargs.get("cwd") == "/my/project"

    def test_context_updated_after_terminal_creation(self):
        """Verify context can be updated after terminal creation but before shell start."""
        detail = self._make_detail()

        # Create terminal without context
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal
        assert term1._project_path is None

        # Set context after creation
        detail.set_project_context("/my/project", "/my/db.db")

        # Context should now be available
        assert term1._project_path == "/my/project"
        assert term1._db_path == "/my/db.db"

        # Start run and verify it works
        with patch.object(term1._terminal, "start_shell") as mock_start, \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1.start_run(ticket_number=1, project_path="/my/project", db_path="/my/db.db")

            mock_start.assert_called_once()

    # -------------------------------------------------------------------------
    # Test: State manager propagation works with delayed init
    # -------------------------------------------------------------------------

    def test_state_manager_available_for_run_guard(self):
        """Verify state manager is available to check for active runs."""
        from unittest.mock import MagicMock
        from levelup.state.manager import StateManager

        detail = self._make_detail()
        detail.set_project_context("/test/project", "/test/db.db")

        # Create mock state manager
        mock_sm = MagicMock(spec=StateManager)
        mock_sm.has_active_run_for_ticket.return_value = None
        detail.set_project_context("/test/project", "/test/db.db", state_manager=mock_sm)

        # Create terminal
        detail.set_ticket(_make_ticket(1))
        term1 = detail._current_terminal

        # State manager should be available
        assert term1._state_manager is mock_sm

        # Starting a run should check for active runs
        with patch.object(term1._terminal, "start_shell"), \
             patch.object(term1._terminal, "send_command"), \
             patch.object(term1._terminal, "setFocus"):
            term1._on_run_clicked()

            # Should have checked for active runs
            mock_sm.has_active_run_for_ticket.assert_called_once_with("/test/project", 1)
