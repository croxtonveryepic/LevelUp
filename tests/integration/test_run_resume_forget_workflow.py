"""Integration tests for the full run/resume/forget workflow.

These tests validate the complete workflow of starting a run, pausing/failing it,
resuming it, and forgetting it, ensuring button states are correct at each step.

Tests follow TDD approach - these tests SHOULD FAIL initially until the
implementation is fixed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


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
class TestRunResumeForgetWorkflow:
    """Integration tests for the complete run/resume/forget workflow."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_workflow_run_fails_resume_completes(self):
        """Test workflow: start run -> run fails -> resume -> run completes."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._ticket_number = 5
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"

        # Mock state manager
        mock_sm = MagicMock(spec=StateManager)
        widget.set_state_manager(mock_sm)

        # Initial state: run should be enabled
        widget._update_button_states()
        assert widget._run_btn.isEnabled() is True, "Initially, run should be enabled"
        assert widget._resume_btn.isEnabled() is False, "Initially, resume should be disabled"

        # Step 1: Start a run (mocked)
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):
            widget.start_run(widget._ticket_number, widget._project_path, widget._db_path)

        assert widget.is_running is True
        assert widget._run_btn.isEnabled() is False, "Run button should be disabled while running"
        assert widget._resume_btn.isEnabled() is False, "Resume button should be disabled while running"
        assert widget._terminate_btn.isEnabled() is True
        assert widget._pause_btn.isEnabled() is True

        # Step 2: Run fails
        widget._last_run_id = "test-run-123"
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record

        widget._set_running_state(False)

        assert widget.is_running is False
        assert widget._run_btn.isEnabled() is False, "Run button should be disabled after failure"
        assert widget._resume_btn.isEnabled() is True, "Resume button should be enabled after failure"
        assert widget._forget_btn.isEnabled() is True, "Forget button should be enabled after failure"

        # Step 3: Resume the run (mocked)
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):
            widget._on_resume_clicked()

        assert widget.is_running is True
        assert widget._run_btn.isEnabled() is False, "Run button should be disabled while resuming"
        assert widget._resume_btn.isEnabled() is False, "Resume button should be disabled while resuming"

        # Step 4: Run completes
        mock_record.status = "completed"
        widget._set_running_state(False)

        assert widget.is_running is False
        assert widget._run_btn.isEnabled() is True, "Run button should be enabled after completion"
        assert widget._resume_btn.isEnabled() is False, "Resume button should be disabled after completion"

    def test_workflow_run_pauses_resume_completes(self):
        """Test workflow: start run -> run pauses -> resume -> run completes."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._ticket_number = 3
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"

        # Mock state manager
        mock_sm = MagicMock(spec=StateManager)
        widget.set_state_manager(mock_sm)

        # Step 1: Start a run
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):
            widget.start_run(widget._ticket_number, widget._project_path, widget._db_path)

        # Step 2: Run pauses
        widget._last_run_id = "test-run-456"
        mock_record = MagicMock()
        mock_record.status = "paused"
        mock_sm.get_run.return_value = mock_record

        widget._set_running_state(False)

        assert widget._run_btn.isEnabled() is False, "Run button should be disabled when paused"
        assert widget._resume_btn.isEnabled() is True, "Resume button should be enabled when paused"

        # Step 3: Resume
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):
            widget._on_resume_clicked()

        # Step 4: Run completes
        mock_record.status = "completed"
        widget._set_running_state(False)

        assert widget._run_btn.isEnabled() is True, "Run button should be enabled after completion"
        assert widget._resume_btn.isEnabled() is False, "Resume button should be disabled after completion"

    def test_workflow_run_fails_forget_then_new_run(self):
        """Test workflow: start run -> run fails -> forget -> start new run."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._ticket_number = 7
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"

        # Mock state manager
        mock_sm = MagicMock(spec=StateManager)
        widget.set_state_manager(mock_sm)

        # Step 1: Start a run
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):
            widget.start_run(widget._ticket_number, widget._project_path, widget._db_path)

        # Step 2: Run fails
        widget._last_run_id = "test-run-789"
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record

        widget._set_running_state(False)

        assert widget._run_btn.isEnabled() is False, "Run button should be disabled after failure"
        assert widget._resume_btn.isEnabled() is True, "Resume button should be enabled after failure"
        assert widget._forget_btn.isEnabled() is True, "Forget button should be enabled"

        # Step 3: Forget the run
        widget._last_run_id = None
        widget._update_button_states()

        assert widget._run_btn.isEnabled() is True, "Run button should be enabled after forgetting"
        assert widget._resume_btn.isEnabled() is False, "Resume button should be disabled after forgetting"
        assert widget._forget_btn.isEnabled() is False, "Forget button should be disabled after forgetting"

        # Step 4: Start a new run
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):
            widget.start_run(widget._ticket_number, widget._project_path, widget._db_path)

        assert widget.is_running is True
        assert widget._run_btn.isEnabled() is False

    def test_workflow_run_aborts_cannot_start_new_until_forget(self):
        """Test that user cannot start new run after abort until they forget or resume."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._ticket_number = 2
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"

        # Mock state manager
        mock_sm = MagicMock(spec=StateManager)
        widget.set_state_manager(mock_sm)

        # Step 1: Start a run
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):
            widget.start_run(widget._ticket_number, widget._project_path, widget._db_path)

        # Step 2: Run is aborted
        widget._last_run_id = "test-run-999"
        mock_record = MagicMock()
        mock_record.status = "aborted"
        mock_sm.get_run.return_value = mock_record

        widget._set_running_state(False)

        # User should NOT be able to start a new run - button should be disabled
        assert widget._run_btn.isEnabled() is False, "Run button should be disabled after abort"
        assert widget._resume_btn.isEnabled() is True, "Resume button should be enabled after abort"

        # Try to click run button (should be no-op since disabled, but testing the guard)
        # The button being disabled prevents the click, but we can test the logic guard too
        mock_sm.has_active_run_for_ticket.return_value = mock_record
        with patch.object(widget._terminal, "send_command") as mock_send:
            # Manually call the handler to test the guard
            widget._on_run_clicked()
            # Should not send command because of the guard in _on_run_clicked
            mock_send.assert_not_called()

    def test_multiple_state_transitions_maintain_consistency(self):
        """Test that multiple rapid state transitions maintain button state consistency."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._ticket_number = 8
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"
        widget._last_run_id = "test-run-multi"

        # Mock state manager
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        widget.set_state_manager(mock_sm)

        # Transition 1: Failed run
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget._set_running_state(False)

        run_1 = widget._run_btn.isEnabled()
        resume_1 = widget._resume_btn.isEnabled()

        # Transition 2: Call update_button_states
        widget._update_button_states()

        run_2 = widget._run_btn.isEnabled()
        resume_2 = widget._resume_btn.isEnabled()

        # Should be consistent
        assert run_1 == run_2, "Run button should remain consistent"
        assert resume_1 == resume_2, "Resume button should remain consistent"

        # Transition 3: Start running
        widget._set_running_state(True)

        assert widget._run_btn.isEnabled() is False
        assert widget._resume_btn.isEnabled() is False

        # Transition 4: Back to failed
        widget._set_running_state(False)

        assert widget._run_btn.isEnabled() is False
        assert widget._resume_btn.isEnabled() is True

    def test_workflow_with_no_ticket_prevents_run(self):
        """Test that run button remains disabled when no ticket is set."""
        widget = self._make_widget()
        widget._ticket_number = None  # No ticket
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"

        widget._update_button_states()

        assert widget._run_btn.isEnabled() is False, "Run button should be disabled without ticket"

        # Even after setting context, without ticket it should stay disabled
        widget.set_context(widget._project_path, widget._db_path)
        widget._update_button_states()

        assert widget._run_btn.isEnabled() is False

    def test_workflow_with_no_project_prevents_run(self):
        """Test that run button remains disabled when no project path is set."""
        widget = self._make_widget()
        widget._ticket_number = 5
        widget._project_path = None  # No project path
        widget._db_path = "/tmp/state.db"

        widget._update_button_states()

        assert widget._run_btn.isEnabled() is False, "Run button should be disabled without project"

    def test_polling_detects_completion_and_updates_buttons(self):
        """Test that polling for run status updates button states correctly."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._ticket_number = 9
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"
        widget._command_running = True
        widget._last_run_id = "test-run-poll"

        # Mock state manager with running status
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "running"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Poll while running - should remain in running state
        widget._run_id_poll_timer.start(1000)
        widget._poll_for_run_id()

        assert widget.is_running is True
        assert widget._run_btn.isEnabled() is False
        assert widget._run_id_poll_timer.isActive() is True

        # Update status to failed
        mock_record.status = "failed"

        # Track emitted signals
        finished_codes: list[int] = []
        widget.run_finished.connect(lambda code: finished_codes.append(code))

        # Poll should detect failure and update button states
        widget._poll_for_run_id()

        assert widget.is_running is False
        assert finished_codes == [1]
        assert widget._run_btn.isEnabled() is False, "Run button should be disabled after polling detects failure"
        assert widget._resume_btn.isEnabled() is True, "Resume button should be enabled after polling detects failure"
        assert widget._run_id_poll_timer.isActive() is False

    def test_workflow_handles_external_run_deletion(self):
        """Test workflow when run is deleted externally while polling."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._ticket_number = 10
        widget._project_path = "/some/project"
        widget._command_running = True
        widget._last_run_id = "test-run-deleted"

        # Mock state manager that returns None (run was deleted)
        mock_sm = MagicMock(spec=StateManager)
        mock_sm.get_run.return_value = None
        widget.set_state_manager(mock_sm)

        widget._run_id_poll_timer.start(1000)
        widget._poll_for_run_id()

        # Widget should transition to not-running
        assert widget.is_running is False
        assert widget._run_id_poll_timer.isActive() is False

    def test_notify_run_finished_respects_resumable_state(self):
        """Test that notify_run_finished sets button states correctly based on resumable status."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._ticket_number = 11
        widget._project_path = "/some/project"
        widget._last_run_id = "test-run-notify"
        widget._command_running = True

        # Mock state manager with failed run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Call notify_run_finished
        widget.notify_run_finished(exit_code=1)

        assert widget.is_running is False
        # The button states should reflect the failed (resumable) status
        # This will fail with current implementation but should pass after fix
        assert widget._run_btn.isEnabled() is False, "Run button should be disabled after failure"
        assert widget._resume_btn.isEnabled() is True, "Resume button should be enabled after failure"


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestUserScenarios:
    """Test realistic user scenarios for the run/resume/forget workflow."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_user_loads_ticket_with_failed_run(self):
        """Scenario: User opens GUI and loads a ticket that has a failed run."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()

        # Simulate loading a ticket via ticket_detail.py
        widget._ticket_number = 15
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"

        # State manager has a failed run for this ticket
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.run_id = "failed-run-abc"
        mock_record.status = "failed"
        mock_sm.get_run_for_ticket.return_value = mock_record
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Simulate _wire_existing_run from ticket_detail.py
        widget._last_run_id = mock_record.run_id

        # Update button states
        widget._update_button_states()

        # User should see: run disabled, resume enabled
        assert widget._run_btn.isEnabled() is False, "Run should be disabled - user must resume or forget"
        assert widget._resume_btn.isEnabled() is True, "Resume should be enabled"
        assert widget._forget_btn.isEnabled() is True, "Forget should be enabled"

    def test_user_loads_ticket_with_completed_run(self):
        """Scenario: User opens GUI and loads a ticket that has a completed run."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()

        widget._ticket_number = 16
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"

        # State manager has a completed run for this ticket
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.run_id = "completed-run-xyz"
        mock_record.status = "completed"
        mock_sm.get_run_for_ticket.return_value = mock_record
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._last_run_id = mock_record.run_id
        widget._update_button_states()

        # User should see: run enabled, resume disabled
        assert widget._run_btn.isEnabled() is True, "Run should be enabled - can start new run"
        assert widget._resume_btn.isEnabled() is False, "Resume should be disabled - run already completed"

    def test_user_loads_ticket_with_no_run(self):
        """Scenario: User opens GUI and loads a ticket that has no previous run."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()

        widget._ticket_number = 17
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"

        # State manager has no run for this ticket
        mock_sm = MagicMock(spec=StateManager)
        mock_sm.get_run_for_ticket.return_value = None
        widget.set_state_manager(mock_sm)

        widget._last_run_id = None
        widget._update_button_states()

        # User should see: run enabled, resume disabled
        assert widget._run_btn.isEnabled() is True, "Run should be enabled - no previous run"
        assert widget._resume_btn.isEnabled() is False, "Resume should be disabled - no previous run"

    def test_user_tries_to_run_when_resumable_exists_sees_warning(self):
        """Scenario: User somehow clicks run button when resumable run exists (should show warning)."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()

        widget._ticket_number = 18
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"

        # State manager has active failed run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.run_id = "active-failed-run"
        mock_record.status = "failed"
        mock_sm.has_active_run_for_ticket.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Mock the message box
        with patch("levelup.gui.run_terminal.QMessageBox.warning") as mock_warning:
            widget._on_run_clicked()

            # Should show warning message
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            assert "Active Run Exists" in call_args[0][1]

    def test_user_resumes_then_run_fails_again(self):
        """Scenario: User resumes a failed run, but it fails again."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()

        widget._ticket_number = 19
        widget._project_path = "/some/project"
        widget._db_path = "/tmp/state.db"
        widget._last_run_id = "retry-run-abc"

        # State manager has failed run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Initial state: resume enabled
        widget._set_running_state(False)
        assert widget._resume_btn.isEnabled() is True

        # User resumes
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):
            widget._on_resume_clicked()

        assert widget.is_running is True

        # Run fails again
        widget._set_running_state(False)

        # Should be able to resume again
        assert widget._run_btn.isEnabled() is False, "Run should be disabled"
        assert widget._resume_btn.isEnabled() is True, "Resume should still be enabled for retry"
