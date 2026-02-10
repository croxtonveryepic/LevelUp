"""Terminal widget for running LevelUp pipelines from the GUI.

Uses an interactive PTY-based terminal emulator instead of a read-only
QPlainTextEdit, so Rich colored output renders correctly and the user
can type commands directly.
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from levelup.gui.terminal_emulator import TerminalEmulatorWidget


def build_run_command(
    ticket_number: int,
    project_path: str,
    db_path: str,
) -> str:
    """Build the shell command string for a GUI pipeline run."""
    python = sys.executable.replace("\\", "/")
    return (
        f'"{python}" -m levelup run'
        f" --gui"
        f" --ticket {ticket_number}"
        f' --path "{project_path}"'
        f' --db-path "{db_path}"'
    )


class RunTerminalWidget(QWidget):
    """Embedded interactive terminal for running ``levelup run --gui``."""

    run_started = pyqtSignal(int)   # PID (emitted as 0 — no separate process PID)
    run_finished = pyqtSignal(int)  # exit code

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._command_running = False
        self._shell_started = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header: status label + buttons
        header = QHBoxLayout()

        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("terminalStatusLabel")
        header.addWidget(self._status_label)
        header.addStretch()

        self._run_btn = QPushButton("Run")
        self._run_btn.setObjectName("runBtn")
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self._on_run_clicked)
        header.addWidget(self._run_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        header.addWidget(self._stop_btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._on_clear)
        header.addWidget(self._clear_btn)

        layout.addLayout(header)

        # Terminal emulator
        self._terminal = TerminalEmulatorWidget()
        self._terminal.shell_exited.connect(self._on_shell_exited)
        layout.addWidget(self._terminal)

        # Pending run parameters (set via set_context / start_run)
        self._ticket_number: int | None = None
        self._project_path: str | None = None
        self._db_path: str | None = None

    # -- Public API ---------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._command_running

    @property
    def process_pid(self) -> int | None:
        return 0 if self._command_running else None

    def set_context(self, project_path: str, db_path: str) -> None:
        """Store project context so the Run button can be enabled."""
        self._project_path = project_path
        self._db_path = db_path

    def start_run(self, ticket_number: int, project_path: str, db_path: str) -> None:
        """Start a pipeline run for the given ticket."""
        if self._command_running:
            return

        self._ticket_number = ticket_number
        self._project_path = project_path
        self._db_path = db_path

        # Ensure the shell is started
        self._ensure_shell()

        cmd = build_run_command(ticket_number, project_path, db_path)
        self._terminal.send_command(cmd)

        self._set_running_state(True)
        self.run_started.emit(0)

    def enable_run(self, enabled: bool) -> None:
        """Enable/disable the Run button (e.g. when a ticket is loaded)."""
        if not self._command_running:
            self._run_btn.setEnabled(enabled)

    def notify_run_finished(self, exit_code: int = 0) -> None:
        """Called externally (e.g. by DB poller) when the pipeline run completes."""
        if not self._command_running:
            return
        self._set_running_state(False)
        status = "completed" if exit_code == 0 else f"exited ({exit_code})"
        self._status_label.setText(f"Finished ({exit_code})")
        self.run_finished.emit(exit_code)

    # -- Internal -----------------------------------------------------------

    def showEvent(self, event: object) -> None:
        super().showEvent(event)  # type: ignore[arg-type]
        self._ensure_shell()

    def _ensure_shell(self) -> None:
        """Start the shell if it hasn't been started yet."""
        if self._shell_started:
            return
        cwd = self._project_path
        self._terminal.start_shell(cwd=cwd)
        self._shell_started = True

    def _set_running_state(self, running: bool) -> None:
        self._command_running = running
        self._run_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._status_label.setText("Running..." if running else "Ready")

    def _on_run_clicked(self) -> None:
        if self._ticket_number is not None and self._project_path and self._db_path:
            self.start_run(self._ticket_number, self._project_path, self._db_path)

    def _on_stop_clicked(self) -> None:
        """Send Ctrl+C to the shell to interrupt the running command."""
        self._terminal.send_interrupt()
        # Give the process a moment, then mark as not running
        self._set_running_state(False)
        self._status_label.setText("Interrupted")
        self.run_finished.emit(1)

    def _on_clear(self) -> None:
        """Send clear command to the shell."""
        self._terminal.send_clear()

    def _on_shell_exited(self, exit_code: int) -> None:
        """Handle the shell itself exiting (not just a command)."""
        self._shell_started = False
        if self._command_running:
            self._set_running_state(False)
            self.run_finished.emit(exit_code)
