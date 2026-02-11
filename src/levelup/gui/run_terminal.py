"""Terminal widget for running LevelUp pipelines from the GUI.

Uses an interactive PTY-based terminal emulator instead of a read-only
QPlainTextEdit, so Rich colored output renders correctly and the user
can type commands directly.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from levelup.core.tickets import TicketStatus
from levelup.gui.terminal_emulator import (
    TerminalEmulatorWidget,
    CatppuccinMochaColors,
    LightTerminalColors,
)

logger = logging.getLogger(__name__)

RESUMABLE_STATUSES = ("failed", "aborted", "paused")


def build_run_command(
    ticket_number: int,
    project_path: str,
    db_path: str,
    *,
    model: str | None = None,
    effort: str | None = None,
    skip_planning: bool = False,
) -> str:
    """Build the shell command string for a GUI pipeline run."""
    python = sys.executable.replace("\\", "/")
    cmd = (
        f'"{python}" -m levelup run'
        f" --ticket {ticket_number}"
        f' --path "{project_path}"'
        f' --db-path "{db_path}"'
    )
    if model:
        cmd += f" --model {model}"
    if effort:
        cmd += f" --effort {effort}"
    if skip_planning:
        cmd += " --skip-planning"
    return cmd


def build_resume_command(
    run_id: str,
    project_path: str,
    db_path: str,
) -> str:
    """Build the shell command string for resuming a pipeline run."""
    python = sys.executable.replace("\\", "/")
    return (
        f'"{python}" -m levelup resume {run_id}'
        f' --path "{project_path}"'
        f' --db-path "{db_path}"'
    )


def build_merge_command(ticket_number: int, project_path: str) -> str:
    """Build the shell command string for merging a ticket's branch."""
    python = sys.executable.replace("\\", "/")
    return (
        f'"{python}" -m levelup merge'
        f" --ticket {ticket_number}"
        f' --path "{project_path}"'
    )


class RunTerminalWidget(QWidget):
    """Embedded interactive terminal for running ``levelup run`` pipelines."""

    run_started = pyqtSignal(int)   # PID (emitted as 0 — no separate process PID)
    run_finished = pyqtSignal(int)  # exit code
    run_paused = pyqtSignal()       # emitted when pause is confirmed via DB
    merge_finished = pyqtSignal()   # emitted when merge operation completes successfully

    def __init__(self, parent: QWidget | None = None, theme: str = "dark") -> None:
        super().__init__(parent)
        self._command_running = False
        self._shell_started = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header: status label + run options + buttons
        header = QHBoxLayout()

        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("terminalStatusLabel")
        header.addWidget(self._status_label)
        header.addStretch()

        # Run option widgets (moved from ticket form)
        header.addWidget(QLabel("Model:"))
        self._model_combo = QComboBox()
        self._model_combo.addItems(["Default", "Sonnet", "Opus"])
        self._model_combo.setCurrentIndex(0)
        header.addWidget(self._model_combo)

        header.addWidget(QLabel("Effort:"))
        self._effort_combo = QComboBox()
        self._effort_combo.addItems(["Default", "Low", "Medium", "High"])
        self._effort_combo.setCurrentIndex(0)
        header.addWidget(self._effort_combo)

        self._skip_planning_checkbox = QCheckBox("Skip planning")
        self._skip_planning_checkbox.setChecked(False)
        header.addWidget(self._skip_planning_checkbox)

        header.addStretch()

        self._run_btn = QPushButton("Run")
        self._run_btn.setObjectName("runBtn")
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self._on_run_clicked)
        header.addWidget(self._run_btn)

        self._terminate_btn = QPushButton("Terminate")
        self._terminate_btn.setObjectName("terminateBtn")
        self._terminate_btn.setEnabled(False)
        self._terminate_btn.clicked.connect(self._on_terminate_clicked)
        header.addWidget(self._terminate_btn)

        self._pause_btn = QPushButton("Pause")
        self._pause_btn.setObjectName("pauseBtn")
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self._on_pause_clicked)
        header.addWidget(self._pause_btn)

        self._resume_btn = QPushButton("Resume")
        self._resume_btn.setObjectName("resumeBtn")
        self._resume_btn.setEnabled(False)
        self._resume_btn.clicked.connect(self._on_resume_clicked)
        header.addWidget(self._resume_btn)

        self._forget_btn = QPushButton("Forget")
        self._forget_btn.setObjectName("forgetBtn")
        self._forget_btn.setEnabled(False)
        self._forget_btn.clicked.connect(self._on_forget_clicked)
        header.addWidget(self._forget_btn)

        self._merge_btn = QPushButton("Merge")
        self._merge_btn.setObjectName("mergeBtn")
        self._merge_btn.setEnabled(False)
        self._merge_btn.clicked.connect(self._on_merge_clicked)
        header.addWidget(self._merge_btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._on_clear)
        header.addWidget(self._clear_btn)

        layout.addLayout(header)

        # Terminal emulator - select color scheme based on theme
        # Normalize theme parameter (case-insensitive, strip whitespace)
        normalized_theme = (theme or "dark").strip().lower()
        color_scheme = LightTerminalColors if normalized_theme == "light" else CatppuccinMochaColors

        self._terminal = TerminalEmulatorWidget(color_scheme=color_scheme)
        self._terminal.shell_exited.connect(self._on_shell_exited)
        layout.addWidget(self._terminal)

        # Pending run parameters (set via set_context / start_run)
        self._ticket_number: int | None = None
        self._project_path: str | None = None
        self._db_path: str | None = None

        # Run tracking
        self._last_run_id: str | None = None
        self._state_manager: object | None = None  # StateManager instance

        # Current ticket reference (for merge operations)
        self._current_ticket: object | None = None  # Ticket instance

        # Timer for polling run_id after starting a run
        self._run_id_poll_timer = QTimer(self)
        self._run_id_poll_timer.timeout.connect(self._poll_for_run_id)

        # Timer for polling merge completion (ticket status -> MERGED)
        self._merge_poll_timer = QTimer(self)
        self._merge_poll_timer.timeout.connect(self._poll_merge_completion)
        self._merge_poll_count = 0

    # -- Public API ---------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._command_running

    @property
    def process_pid(self) -> int | None:
        return 0 if self._command_running else None

    @property
    def last_run_id(self) -> str | None:
        return self._last_run_id

    def set_context(self, project_path: str, db_path: str) -> None:
        """Store project context so the Run button can be enabled."""
        self._project_path = project_path
        self._db_path = db_path

    def set_state_manager(self, sm: object) -> None:
        """Store a StateManager reference for pause/resume/forget operations."""
        self._state_manager = sm

    def start_run(self, ticket_number: int, project_path: str, db_path: str) -> None:
        """Start a pipeline run for the given ticket."""
        if self._command_running:
            return

        self._ticket_number = ticket_number
        self._project_path = project_path
        self._db_path = db_path
        self._last_run_id = None

        # Ensure the shell is started
        self._ensure_shell()

        # Read run options from widget combos/checkbox
        model_idx = self._model_combo.currentIndex()
        model = None
        if model_idx == 1:
            model = "sonnet"
        elif model_idx == 2:
            model = "opus"

        effort_idx = self._effort_combo.currentIndex()
        effort = None
        if effort_idx == 1:
            effort = "low"
        elif effort_idx == 2:
            effort = "medium"
        elif effort_idx == 3:
            effort = "high"

        skip_planning = self._skip_planning_checkbox.isChecked()

        cmd = build_run_command(
            ticket_number, project_path, db_path,
            model=model,
            effort=effort,
            skip_planning=skip_planning,
        )
        self._terminal.send_command(cmd)
        self._terminal.setFocus()

        self._set_running_state(True)
        self.run_started.emit(0)

        # Start polling for run_id
        self._run_id_poll_timer.start(1000)

    def enable_run(self, enabled: bool) -> None:
        """Enable/disable the Run button (e.g. when a ticket is loaded)."""
        if not self._command_running:
            # Only enable if enabled=True and no resumable run exists
            if enabled and not self._is_resumable():
                self._run_btn.setEnabled(True)
            elif not enabled:
                self._run_btn.setEnabled(False)
            # else: enabled=True but resumable run exists, so keep disabled

    def notify_run_finished(self, exit_code: int = 0) -> None:
        """Called externally (e.g. by DB poller) when the pipeline run completes."""
        if not self._command_running:
            return
        self._set_running_state(False)
        self._status_label.setText(f"Finished ({exit_code})")
        self.run_finished.emit(exit_code)

    def set_ticket(self, ticket: object) -> None:
        """Store the current ticket reference for merge operations."""
        self._current_ticket = ticket
        self._update_button_states()

    # -- Internal -----------------------------------------------------------

    def showEvent(self, event: object) -> None:
        super().showEvent(event)  # type: ignore[arg-type]

    def _ensure_shell(self) -> None:
        """Start the shell if it hasn't been started yet."""
        if self._shell_started:
            return
        cwd = self._project_path
        self._terminal.start_shell(cwd=cwd)
        self._shell_started = True

    def _set_running_state(self, running: bool) -> None:
        self._command_running = running
        # Only enable run button if not running AND no resumable run exists
        self._run_btn.setEnabled(not running and not self._is_resumable())
        self._terminate_btn.setEnabled(running)
        self._pause_btn.setEnabled(running)
        self._resume_btn.setEnabled(not running and self._is_resumable())
        self._forget_btn.setEnabled(not running and self._last_run_id is not None)
        self._merge_btn.setEnabled(not running and self._can_merge())
        self._status_label.setText("Running..." if running else "Ready")

        # Lock run options while running
        self._model_combo.setEnabled(not running and self._last_run_id is None)
        self._effort_combo.setEnabled(not running and self._last_run_id is None)
        self._skip_planning_checkbox.setEnabled(not running and self._last_run_id is None)

        # Update tooltips when locked
        if running or self._last_run_id is not None:
            tooltip = "Run options are locked while a run exists for this ticket. Use 'Forget' to unlock."
            self._model_combo.setToolTip(tooltip)
            self._effort_combo.setToolTip(tooltip)
            self._skip_planning_checkbox.setToolTip(tooltip)
        else:
            self._model_combo.setToolTip("")
            self._effort_combo.setToolTip("")
            self._skip_planning_checkbox.setToolTip("Skip the planning step for this run")

    def _update_button_states(self) -> None:
        """Refresh button enabled/disabled states based on current state."""
        running = self._command_running
        # Only enable run button if not running, has context, AND no resumable run exists
        self._run_btn.setEnabled(
            not running and self._ticket_number is not None and self._project_path is not None
            and not self._is_resumable()
        )
        self._terminate_btn.setEnabled(running)
        self._pause_btn.setEnabled(running)
        self._resume_btn.setEnabled(not running and self._is_resumable())
        self._forget_btn.setEnabled(not running and self._last_run_id is not None)
        self._merge_btn.setEnabled(not running and self._can_merge())

        # Lock run options if a run exists (even if not currently running)
        has_run = self._last_run_id is not None
        self._model_combo.setEnabled(not running and not has_run)
        self._effort_combo.setEnabled(not running and not has_run)
        self._skip_planning_checkbox.setEnabled(not running and not has_run)

        # Update tooltips when locked
        if has_run:
            tooltip = "Run options are locked while a run exists for this ticket. Use 'Forget' to unlock."
            self._model_combo.setToolTip(tooltip)
            self._effort_combo.setToolTip(tooltip)
            self._skip_planning_checkbox.setToolTip(tooltip)
        else:
            self._model_combo.setToolTip("")
            self._effort_combo.setToolTip("")
            self._skip_planning_checkbox.setToolTip("Skip the planning step for this run")

    def _is_resumable(self) -> bool:
        """Check if the last run has a resumable status."""
        if not self._last_run_id or not self._state_manager:
            return False
        from levelup.state.manager import StateManager

        assert isinstance(self._state_manager, StateManager)
        record = self._state_manager.get_run(self._last_run_id)
        if record is None:
            return False
        return record.status in RESUMABLE_STATUSES

    def _can_merge(self) -> bool:
        """Check if merge button should be enabled."""
        if not self._project_path or not self._db_path or not self._current_ticket:
            return False

        from levelup.core.tickets import TicketStatus

        # Only enable merge for tickets with status DONE and branch_name metadata
        if not hasattr(self._current_ticket, 'status') or not hasattr(self._current_ticket, 'metadata'):
            return False

        if self._current_ticket.status != TicketStatus.DONE:
            return False

        if not self._current_ticket.metadata:
            return False

        branch_name = self._current_ticket.metadata.get('branch_name', '')
        return bool(branch_name and branch_name.strip())

    def _on_run_clicked(self) -> None:
        if self._ticket_number is not None and self._project_path and self._db_path:
            # Guard: check for existing active run for this ticket
            if self._state_manager and self._ticket_number:
                from levelup.state.manager import StateManager

                assert isinstance(self._state_manager, StateManager)
                active = self._state_manager.has_active_run_for_ticket(
                    self._project_path, self._ticket_number
                )
                if active:
                    QMessageBox.warning(
                        self,
                        "Active Run Exists",
                        f"Ticket #{self._ticket_number} already has an active run "
                        f"({active.run_id[:12]}, status={active.status}).\n"
                        "Resume or forget it first.",
                    )
                    return
            self.start_run(self._ticket_number, self._project_path, self._db_path)

    def _on_terminate_clicked(self) -> None:
        """Kill the running process and mark as failed."""
        # Send interrupt first
        self._terminal.send_interrupt()

        # If we have a run_id, mark it as failed in the DB
        if self._last_run_id and self._state_manager:
            from levelup.state.manager import StateManager

            assert isinstance(self._state_manager, StateManager)
            record = self._state_manager.get_run(self._last_run_id)
            if record and record.pid:
                try:
                    if os.name == "nt":
                        os.system(f"taskkill /F /PID {record.pid} >nul 2>&1")
                    else:
                        import signal

                        os.kill(record.pid, signal.SIGKILL)
                except OSError:
                    pass

            # Update DB status
            conn = self._state_manager._conn()
            try:
                conn.execute(
                    "UPDATE runs SET status = 'failed', error_message = 'Terminated by user', updated_at = datetime('now') WHERE run_id = ?",
                    (self._last_run_id,),
                )
                conn.commit()
            finally:
                conn.close()

        self._set_running_state(False)
        self._status_label.setText("Terminated")
        self.run_finished.emit(1)

    def _on_pause_clicked(self) -> None:
        """Request a pause via the state DB."""
        if not self._last_run_id or not self._state_manager:
            return
        from levelup.state.manager import StateManager

        assert isinstance(self._state_manager, StateManager)
        self._state_manager.request_pause(self._last_run_id)
        self._pause_btn.setEnabled(False)
        self._status_label.setText("Pausing...")

    def _on_resume_clicked(self) -> None:
        """Resume the last run via the terminal."""
        if not self._last_run_id or not self._project_path or not self._db_path:
            return
        if self._command_running:
            return

        self._ensure_shell()

        cmd = build_resume_command(self._last_run_id, self._project_path, self._db_path)
        self._terminal.send_command(cmd)
        self._terminal.setFocus()

        self._set_running_state(True)
        self.run_started.emit(0)

        # Start polling for completion detection
        self._run_id_poll_timer.start(1000)

    def _on_forget_clicked(self) -> None:
        """Delete the last run from the state DB."""
        if not self._last_run_id or not self._state_manager:
            return

        reply = QMessageBox.question(
            self,
            "Forget Run",
            f"Delete run '{self._last_run_id[:12]}' from the database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from levelup.state.manager import StateManager

        assert isinstance(self._state_manager, StateManager)
        self._state_manager.delete_run(self._last_run_id)
        self._last_run_id = None
        self._update_button_states()
        self._status_label.setText("Run forgotten")

    def _on_clear(self) -> None:
        """Send clear command to the shell."""
        self._terminal.send_clear()

    def _on_shell_exited(self, exit_code: int) -> None:
        """Handle the shell itself exiting (not just a command)."""
        self._shell_started = False
        self._run_id_poll_timer.stop()
        self._merge_poll_timer.stop()
        if self._command_running:
            self._set_running_state(False)
            self.run_finished.emit(exit_code)

    def _poll_for_run_id(self) -> None:
        """Poll the DB to find the run_id and detect run completion."""
        if not self._state_manager or not self._project_path:
            self._run_id_poll_timer.stop()
            return

        from levelup.state.manager import StateManager

        assert isinstance(self._state_manager, StateManager)

        # If we already have a run_id, check its status for completion
        if self._last_run_id:
            record = self._state_manager.get_run(self._last_run_id)
            if record is None:
                # Run was deleted externally
                self._run_id_poll_timer.stop()
                if self._command_running:
                    self._set_running_state(False)
                return

            if record.status in ("completed", "failed", "aborted"):
                self._run_id_poll_timer.stop()
                if self._command_running:
                    exit_code = 0 if record.status == "completed" else 1
                    self._set_running_state(False)
                    self._status_label.setText(f"Finished ({record.status})")
                    self.run_finished.emit(exit_code)
                else:
                    self._update_button_states()
                return

            if record.status == "paused":
                self._run_id_poll_timer.stop()
                if self._command_running:
                    self._set_running_state(False)
                    self._status_label.setText("Paused")
                    self.run_paused.emit()
                self._update_button_states()
                return

            # Still running — keep polling
            return

        # No run_id yet — search by ticket_number if available, else by project_path
        if self._ticket_number is not None:
            record = self._state_manager.get_run_for_ticket(
                self._project_path, self._ticket_number
            )
            if record is not None:
                self._last_run_id = record.run_id
                if record.status in ("completed", "failed", "aborted"):
                    self._run_id_poll_timer.stop()
                    if self._command_running:
                        exit_code = 0 if record.status == "completed" else 1
                        self._set_running_state(False)
                        self._status_label.setText(f"Finished ({record.status})")
                        self.run_finished.emit(exit_code)
                    else:
                        self._update_button_states()
                else:
                    self._update_button_states()
                return
        else:
            # Fallback: search by project_path (legacy path)
            runs = self._state_manager.list_runs()
            for run in runs:
                if (
                    run.project_path.rstrip("/\\") == self._project_path.rstrip("/\\")
                    and run.status not in ("completed", "failed", "aborted")
                ):
                    self._last_run_id = run.run_id
                    self._update_button_states()
                    return

            # Fallback: check if a run just completed (e.g. very fast run)
            for run in runs:
                if run.project_path.rstrip("/\\") == self._project_path.rstrip("/\\"):
                    self._last_run_id = run.run_id
                    if run.status in ("completed", "failed", "aborted"):
                        self._run_id_poll_timer.stop()
                        if self._command_running:
                            exit_code = 0 if run.status == "completed" else 1
                            self._set_running_state(False)
                            self._status_label.setText(f"Finished ({run.status})")
                            self.run_finished.emit(exit_code)
                        else:
                            self._update_button_states()
                    return

    def _on_merge_clicked(self) -> None:
        """Handle merge button click — runs ``levelup merge`` in the terminal."""
        if not self._current_ticket or not self._project_path:
            return

        if self._command_running:
            return

        # Extract branch_name from ticket metadata
        if not hasattr(self._current_ticket, 'metadata') or not self._current_ticket.metadata:
            return

        branch_name = self._current_ticket.metadata.get('branch_name', '')
        if not branch_name or not branch_name.strip():
            return

        if not hasattr(self._current_ticket, 'number'):
            return

        self._ensure_shell()

        cmd = build_merge_command(self._current_ticket.number, self._project_path)
        self._terminal.send_command(cmd)
        self._terminal.setFocus()

        self._set_running_state(True)
        self._status_label.setText("Merging...")

        # Start polling for merge completion (ticket status → MERGED)
        self._merge_poll_count = 0
        self._merge_poll_timer.start(2000)

    def _poll_merge_completion(self) -> None:
        """Poll ticket file to detect when the merge CLI marks the ticket as MERGED."""
        self._merge_poll_count += 1

        # Timeout after ~60s (30 polls × 2s)
        if self._merge_poll_count >= 30:
            self._merge_poll_timer.stop()
            if self._command_running:
                self._set_running_state(False)
                self._status_label.setText("Merge timed out")
            return

        if not self._current_ticket or not self._project_path:
            self._merge_poll_timer.stop()
            return

        try:
            from levelup.core.tickets import read_tickets

            ticket_num = self._current_ticket.number
            tickets_list = read_tickets(Path(self._project_path))
            for tk in tickets_list:
                if tk.number == ticket_num and tk.status == TicketStatus.MERGED:
                    self._merge_poll_timer.stop()
                    self._set_running_state(False)
                    self._status_label.setText("Merge completed")
                    self.merge_finished.emit()
                    return
        except Exception:
            pass
