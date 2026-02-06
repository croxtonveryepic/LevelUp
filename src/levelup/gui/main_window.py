"""Main dashboard window for monitoring LevelUp pipeline runs."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from levelup.gui.checkpoint_dialog import CheckpointDialog
from levelup.gui.resources import STATUS_COLORS, STATUS_LABELS, status_display
from levelup.state.manager import StateManager
from levelup.state.models import RunRecord

REFRESH_INTERVAL_MS = 2000
COLUMNS = ["Run ID", "Task", "Project", "Status", "Step", "Started"]


class MainWindow(QMainWindow):
    """Dashboard window showing all LevelUp runs."""

    def __init__(self, state_manager: StateManager) -> None:
        super().__init__()
        self._state_manager = state_manager
        self._runs: list[RunRecord] = []

        self.setWindowTitle("LevelUp Dashboard")
        self.setMinimumSize(900, 500)
        self._build_ui()
        self._start_refresh_timer()
        self._refresh()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Toolbar buttons
        toolbar_layout = QHBoxLayout()
        toolbar_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        toolbar_layout.addWidget(refresh_btn)

        cleanup_btn = QPushButton("Clean Up")
        cleanup_btn.setToolTip("Remove completed and failed runs")
        cleanup_btn.clicked.connect(self._cleanup_runs)
        toolbar_layout.addWidget(cleanup_btn)

        layout.addLayout(toolbar_layout)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.doubleClicked.connect(self._on_double_click)

        header = self._table.horizontalHeader()
        assert header is not None
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

    def _start_refresh_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(REFRESH_INTERVAL_MS)

    def _refresh(self) -> None:
        """Reload runs from DB and update the table."""
        self._state_manager.mark_dead_runs()
        self._runs = self._state_manager.list_runs()
        self._update_table()
        self._update_status_bar()

    def _update_table(self) -> None:
        self._table.setRowCount(len(self._runs))

        for row, run in enumerate(self._runs):
            self._table.setItem(row, 0, QTableWidgetItem(run.run_id[:12]))
            self._table.setItem(row, 1, QTableWidgetItem(run.task_title))
            self._table.setItem(row, 2, QTableWidgetItem(run.project_path))

            # Status cell with color
            status_item = QTableWidgetItem(status_display(run.status))
            color = STATUS_COLORS.get(run.status, "#CDD6F4")
            status_item.setForeground(QColor(color))
            self._table.setItem(row, 3, status_item)

            self._table.setItem(row, 4, QTableWidgetItem(run.current_step or ""))
            self._table.setItem(row, 5, QTableWidgetItem(run.started_at[:19]))

    def _update_status_bar(self) -> None:
        active = sum(1 for r in self._runs if r.status in ("running", "pending"))
        awaiting = sum(1 for r in self._runs if r.status == "waiting_for_input")
        self._status_bar.showMessage(
            f"{active} active, {awaiting} awaiting input  |  "
            f"{len(self._runs)} total runs"
        )

    def _on_double_click(self, index: object) -> None:
        """Open checkpoint dialog if the run is waiting for input."""
        row = index.row()  # type: ignore[union-attr]
        if row < 0 or row >= len(self._runs):
            return

        run = self._runs[row]
        if run.status != "waiting_for_input":
            return

        # Find pending checkpoint for this run
        pending = self._state_manager.get_pending_checkpoints()
        for cp in pending:
            if cp.run_id == run.run_id:
                dialog = CheckpointDialog(cp, self._state_manager, parent=self)
                dialog.exec()
                self._refresh()
                return

    def _show_context_menu(self, position: object) -> None:
        """Right-click context menu."""
        index = self._table.indexAt(position)  # type: ignore[arg-type]
        if not index.isValid():
            return

        row = index.row()
        if row < 0 or row >= len(self._runs):
            return

        run = self._runs[row]

        menu = QMenu(self)

        view_action = QAction("View Details", self)
        view_action.triggered.connect(lambda: self._view_details(run))
        menu.addAction(view_action)

        if run.status in ("completed", "failed", "aborted"):
            remove_action = QAction("Remove from List", self)
            remove_action.triggered.connect(lambda: self._remove_run(run))
            menu.addAction(remove_action)

        menu.exec(self._table.viewport().mapToGlobal(position))  # type: ignore[arg-type]

    def _view_details(self, run: RunRecord) -> None:
        """Show run details in a message box."""
        msg = (
            f"Run ID: {run.run_id}\n"
            f"Task: {run.task_title}\n"
            f"Description: {run.task_description}\n"
            f"Project: {run.project_path}\n"
            f"Status: {run.status}\n"
            f"Step: {run.current_step or 'N/A'}\n"
            f"Language: {run.language or 'N/A'}\n"
            f"Framework: {run.framework or 'N/A'}\n"
            f"Test Runner: {run.test_runner or 'N/A'}\n"
            f"Error: {run.error_message or 'None'}\n"
            f"Started: {run.started_at}\n"
            f"Updated: {run.updated_at}\n"
            f"PID: {run.pid}"
        )
        QMessageBox.information(self, f"Run {run.run_id[:12]}", msg)

    def _remove_run(self, run: RunRecord) -> None:
        """Remove a completed/failed/aborted run from the DB."""
        self._state_manager.delete_run(run.run_id)
        self._refresh()

    def _cleanup_runs(self) -> None:
        """Remove all completed and failed runs."""
        to_remove = [r for r in self._runs if r.status in ("completed", "failed", "aborted")]
        if not to_remove:
            QMessageBox.information(self, "Clean Up", "No runs to clean up.")
            return

        reply = QMessageBox.question(
            self, "Clean Up",
            f"Remove {len(to_remove)} completed/failed/aborted runs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for r in to_remove:
                self._state_manager.delete_run(r.run_id)
            self._refresh()
