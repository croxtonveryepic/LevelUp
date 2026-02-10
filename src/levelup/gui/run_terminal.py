"""Terminal widget for running LevelUp pipelines from the GUI."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QProcess, QProcessEnvironment, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

MAX_OUTPUT_LINES = 10_000


def build_command(
    ticket_number: int,
    project_path: str,
    db_path: str,
) -> list[str]:
    """Build the command-line arguments for a GUI pipeline run."""
    return [
        "-m", "levelup", "run",
        "--gui",
        "--ticket", str(ticket_number),
        "--path", project_path,
        "--db-path", db_path,
    ]


class RunTerminalWidget(QWidget):
    """Embedded terminal that spawns ``levelup run --gui`` via QProcess."""

    run_started = pyqtSignal(int)   # PID
    run_finished = pyqtSignal(int)  # exit code

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._process: QProcess | None = None

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

        # Output area
        self._output = QPlainTextEdit()
        self._output.setObjectName("terminalOutput")
        self._output.setReadOnly(True)
        self._output.setMaximumBlockCount(MAX_OUTPUT_LINES)
        layout.addWidget(self._output)

        # Pending run parameters (set via set_context / start_run)
        self._ticket_number: int | None = None
        self._project_path: str | None = None
        self._db_path: str | None = None

    # -- Public API ---------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning

    @property
    def process_pid(self) -> int | None:
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            pid = self._process.processId()
            return pid if pid else None
        return None

    def set_context(self, project_path: str, db_path: str) -> None:
        """Store project context so the Run button can be enabled."""
        self._project_path = project_path
        self._db_path = db_path

    def start_run(self, ticket_number: int, project_path: str, db_path: str) -> None:
        """Start a pipeline run for the given ticket."""
        if self.is_running:
            return

        self._ticket_number = ticket_number
        self._project_path = project_path
        self._db_path = db_path

        args = build_command(ticket_number, project_path, db_path)

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        # Set NO_COLOR=1 so Rich outputs plain text
        env = QProcessEnvironment.systemEnvironment()
        env.insert("NO_COLOR", "1")
        self._process.setProcessEnvironment(env)

        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.finished.connect(self._on_finished)

        self._set_running_state(True)
        self._output.appendPlainText(f">>> levelup run --gui --ticket {ticket_number}\n")

        self._process.start(sys.executable, args)

        # Emit PID once started
        self._process.started.connect(self._emit_started)

    def enable_run(self, enabled: bool) -> None:
        """Enable/disable the Run button (e.g. when a ticket is loaded)."""
        if not self.is_running:
            self._run_btn.setEnabled(enabled)

    # -- Internal -----------------------------------------------------------

    def _set_running_state(self, running: bool) -> None:
        self._run_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._status_label.setText("Running..." if running else "Ready")

    def _emit_started(self) -> None:
        if self._process is not None:
            pid = self._process.processId()
            if pid:
                self.run_started.emit(pid)

    def _on_run_clicked(self) -> None:
        if self._ticket_number is not None and self._project_path and self._db_path:
            self.start_run(self._ticket_number, self._project_path, self._db_path)

    def _on_stop_clicked(self) -> None:
        if self._process is None:
            return
        self._process.terminate()
        if not self._process.waitForFinished(3000):
            self._process.kill()

    def _on_clear(self) -> None:
        self._output.clear()

    def _on_stdout(self) -> None:
        if self._process is None:
            return
        data = self._process.readAllStandardOutput()
        if data:
            text = bytes(data).decode("utf-8", errors="replace")
            self._output.appendPlainText(text.rstrip("\n"))

    def _on_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._set_running_state(False)
        status = "completed" if exit_code == 0 else f"exited ({exit_code})"
        self._output.appendPlainText(f"\n>>> Pipeline {status}")
        self._status_label.setText(f"Finished ({exit_code})")
        self.run_finished.emit(exit_code)
