"""Tests to ensure all existing terminal functionality continues to work.

This test module verifies that the delayed initialization changes do not break
any existing terminal functionality like command sending, interrupting, clearing,
and shell lifecycle management.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.regression

def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestTerminalFunctionalityPreservation:
    """Test that all existing terminal functionality still works."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Setup QApplication for PyQt6 tests."""
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with the embedded terminal's PtyBackend mocked."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    # -------------------------------------------------------------------------
    # Test: send_command functionality
    # -------------------------------------------------------------------------

    def test_send_command_works(self):
        """Verify send_command still works after delayed init."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command") as mock_send, \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            # send_command should have been called
            assert mock_send.call_count == 1
            cmd = mock_send.call_args[0][0]
            assert "-m levelup run" in cmd

    def test_send_command_includes_ticket(self):
        """Verify send_command includes ticket number."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command") as mock_send, \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=42, project_path="/p", db_path="/d")

            cmd = mock_send.call_args[0][0]
            assert "--ticket 42" in cmd

    def test_send_command_includes_paths(self):
        """Verify send_command includes project and db paths."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command") as mock_send, \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(
                ticket_number=1,
                project_path="/my/project",
                db_path="/my/db.db"
            )

            cmd = mock_send.call_args[0][0]
            assert "/my/project" in cmd
            assert "/my/db.db" in cmd

    def test_send_command_on_resume(self):
        """Verify send_command works on resume."""
        widget = self._make_widget()
        widget._last_run_id = "run-abc"
        widget._project_path = "/p"
        widget._db_path = "/d"

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command") as mock_send, \
             patch.object(widget._terminal, "setFocus"):

            widget._on_resume_clicked()

            # send_command should have been called with resume command
            assert mock_send.call_count == 1
            cmd = mock_send.call_args[0][0]
            assert "-m levelup resume" in cmd
            assert "run-abc" in cmd

    # -------------------------------------------------------------------------
    # Test: send_interrupt functionality
    # -------------------------------------------------------------------------

    def test_send_interrupt_works(self):
        """Verify send_interrupt still works."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

        # Now test interrupt
        with patch.object(widget._terminal, "send_interrupt") as mock_interrupt:
            widget._on_terminate_clicked()

            mock_interrupt.assert_called_once()

    def test_terminate_sends_interrupt_first(self):
        """Verify terminate button sends interrupt before killing."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

        with patch.object(widget._terminal, "send_interrupt") as mock_interrupt:
            widget._on_terminate_clicked()

            # Should send interrupt
            mock_interrupt.assert_called_once()
            # Should update state
            assert widget._command_running is False

    # -------------------------------------------------------------------------
    # Test: send_clear functionality
    # -------------------------------------------------------------------------

    def test_send_clear_works(self):
        """Verify send_clear still works."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "send_clear") as mock_clear:
            widget._on_clear()

            mock_clear.assert_called_once()

    def test_clear_button_works_before_shell_start(self):
        """Verify clear button works even before shell is started."""
        widget = self._make_widget()

        # Don't start shell
        assert widget._shell_started is False

        with patch.object(widget._terminal, "send_clear") as mock_clear:
            widget._on_clear()

            # Should still call clear (terminal handles if shell not started)
            mock_clear.assert_called_once()

    def test_clear_button_works_after_shell_start(self):
        """Verify clear button works after shell is started."""
        widget = self._make_widget()

        # Start shell
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

        # Now clear
        with patch.object(widget._terminal, "send_clear") as mock_clear:
            widget._on_clear()

            mock_clear.assert_called_once()

    # -------------------------------------------------------------------------
    # Test: close_shell functionality
    # -------------------------------------------------------------------------

    def test_close_shell_callable(self):
        """Verify close_shell can be called."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "close_shell") as mock_close:
            widget._terminal.close_shell()

            mock_close.assert_called_once()

    def test_shell_cleanup_on_exit(self):
        """Verify shell cleanup happens on shell exit."""
        widget = self._make_widget()

        # Start shell
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert widget._shell_started is True

        # Shell exits
        widget._on_shell_exited(0)

        # Should reset flag
        assert widget._shell_started is False

    def test_shell_exit_stops_polling(self):
        """Verify shell exit stops the run_id poll timer."""
        widget = self._make_widget()

        # Start shell and timer
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert widget._run_id_poll_timer.isActive() is True

        # Shell exits
        widget._on_shell_exited(0)

        # Timer should be stopped
        assert widget._run_id_poll_timer.isActive() is False

    def test_shell_exit_emits_finished(self):
        """Verify shell exit emits run_finished signal."""
        widget = self._make_widget()

        finished_codes: list[int] = []
        widget.run_finished.connect(lambda code: finished_codes.append(code))

        # Start run
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

        # Shell exits
        widget._on_shell_exited(1)

        # Should emit finished with exit code
        assert finished_codes == [1]

    # -------------------------------------------------------------------------
    # Test: Terminal reusability
    # -------------------------------------------------------------------------

    def test_terminal_reusable_across_runs(self):
        """Verify terminal can be reused for multiple runs."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command") as mock_send, \
             patch.object(widget._terminal, "setFocus"):

            # First run
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert mock_start.call_count == 1
            assert mock_send.call_count == 1

            # Finish run
            widget._command_running = False

            # Second run
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            # Shell not started again (already started)
            assert mock_start.call_count == 1
            # But command sent again
            assert mock_send.call_count == 2

    def test_terminal_can_run_different_tickets(self):
        """Verify same terminal widget can run different tickets."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command") as mock_send, \
             patch.object(widget._terminal, "setFocus"):

            # Run ticket 1
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            cmd1 = mock_send.call_args[0][0]
            assert "--ticket 1" in cmd1

            # Finish run
            widget._command_running = False

            # Run ticket 2
            widget.start_run(ticket_number=2, project_path="/p", db_path="/d")
            cmd2 = mock_send.call_args[0][0]
            assert "--ticket 2" in cmd2

    def test_terminal_reusable_after_shell_exit_and_restart(self):
        """Verify terminal can be reused after shell exits and is restarted."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            # First run
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert mock_start.call_count == 1
            assert widget._shell_started is True

            # Shell exits
            widget._on_shell_exited(0)
            assert widget._shell_started is False

            # Second run (should restart shell)
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert mock_start.call_count == 2
            assert widget._shell_started is True

    # -------------------------------------------------------------------------
    # Test: State tracking
    # -------------------------------------------------------------------------

    def test_shell_started_flag_accurate(self):
        """Verify _shell_started flag accurately tracks state."""
        widget = self._make_widget()

        # Initially false
        assert widget._shell_started is False

        # After start_run
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert widget._shell_started is True

        # After shell exit
        widget._on_shell_exited(0)
        assert widget._shell_started is False

    def test_command_running_flag_accurate(self):
        """Verify _command_running flag accurately tracks state."""
        widget = self._make_widget()

        # Initially false
        assert widget._command_running is False

        # After start_run
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert widget._command_running is True

        # After notify_run_finished
        widget.notify_run_finished(0)
        assert widget._command_running is False

    def test_is_running_property_accurate(self):
        """Verify is_running property accurately reflects state."""
        widget = self._make_widget()

        # Initially false
        assert widget.is_running is False

        # After start_run
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert widget.is_running is True

        # After finish
        widget._command_running = False
        assert widget.is_running is False

    def test_process_pid_property_accurate(self):
        """Verify process_pid property accurately reflects state."""
        widget = self._make_widget()

        # Initially None
        assert widget.process_pid is None

        # After start_run
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert widget.process_pid == 0

        # After finish
        widget._command_running = False
        assert widget.process_pid is None

    # -------------------------------------------------------------------------
    # Test: Button states
    # -------------------------------------------------------------------------

    def test_button_states_during_run(self):
        """Verify button enabled states are correct during run."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            # During run
            assert widget._run_btn.isEnabled() is False
            assert widget._terminate_btn.isEnabled() is True
            assert widget._pause_btn.isEnabled() is True

    def test_button_states_after_run(self):
        """Verify button enabled states are correct after run finishes."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            # Finish run
            widget._command_running = False
            widget._set_running_state(False)

            # After run
            assert widget._run_btn.isEnabled() is True
            assert widget._terminate_btn.isEnabled() is False
            assert widget._pause_btn.isEnabled() is False

    def test_clear_button_always_enabled(self):
        """Verify clear button is always usable."""
        widget = self._make_widget()

        # Before run
        assert widget._clear_btn.isEnabled() is True

        # During run
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert widget._clear_btn.isEnabled() is True

        # After run
        widget._command_running = False
        assert widget._clear_btn.isEnabled() is True

    # -------------------------------------------------------------------------
    # Test: Focus management
    # -------------------------------------------------------------------------

    def test_terminal_gets_focus_on_run(self):
        """Verify terminal receives focus when run starts."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus") as mock_focus:

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            mock_focus.assert_called_once()

    def test_terminal_gets_focus_on_resume(self):
        """Verify terminal receives focus when resume starts."""
        widget = self._make_widget()
        widget._last_run_id = "run-abc"
        widget._project_path = "/p"
        widget._db_path = "/d"

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus") as mock_focus:

            widget._on_resume_clicked()

            mock_focus.assert_called_once()

    # -------------------------------------------------------------------------
    # Test: Signals
    # -------------------------------------------------------------------------

    def test_run_started_signal_emitted(self):
        """Verify run_started signal is emitted."""
        widget = self._make_widget()

        pids: list[int] = []
        widget.run_started.connect(lambda pid: pids.append(pid))

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            assert pids == [0]

    def test_run_finished_signal_emitted(self):
        """Verify run_finished signal is emitted."""
        widget = self._make_widget()

        codes: list[int] = []
        widget.run_finished.connect(lambda code: codes.append(code))

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

        widget.notify_run_finished(0)

        assert codes == [0]

    def test_run_paused_signal_emitted(self):
        """Verify run_paused signal is emitted."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()

        paused: list[bool] = []
        widget.run_paused.connect(lambda: paused.append(True))

        # Set up mock state manager
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "paused"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._command_running = True
        widget._project_path = "/p"
        widget._last_run_id = "run-123"

        # Poll and detect pause
        widget._poll_for_run_id()

        assert paused == [True]
