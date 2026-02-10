"""Main dashboard window for monitoring LevelUp pipeline runs."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QApplication,
)

from levelup.gui.checkpoint_dialog import CheckpointDialog
from levelup.gui.resources import STATUS_COLORS, STATUS_LABELS, status_display
from levelup.gui.ticket_detail import TicketDetailWidget
from levelup.gui.ticket_sidebar import TicketSidebarWidget
from levelup.gui.theme_manager import get_current_theme, apply_theme, set_theme_preference, get_theme_preference
from levelup.state.manager import StateManager
from levelup.state.models import RunRecord

REFRESH_INTERVAL_MS = 2000
COLUMNS = ["Run ID", "Task", "Project", "Status", "Step", "Started"]


class MainWindow(QMainWindow):
    """Dashboard window showing all LevelUp runs and tickets."""

    def __init__(
        self,
        state_manager: StateManager,
        project_path: Path | None = None,
    ) -> None:
        super().__init__()
        self._state_manager = state_manager
        self._runs: list[RunRecord] = []
        self._project_path = project_path
        self._tickets_file: str | None = None
        self._db_path = str(state_manager._db_path)
        self._active_run_pids: set[int] = set()
        self._checkpoint_dialog_open = False

        # Load tickets_file setting if we have a project path
        if project_path is not None:
            try:
                from levelup.config.loader import load_settings

                settings = load_settings(project_path=project_path)
                self._tickets_file = settings.project.tickets_file
            except Exception:
                pass

        self.setWindowTitle("LevelUp Dashboard")
        self.setMinimumSize(1000, 550)
        self._build_ui()
        self._start_refresh_timer()
        self._refresh()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Toolbar buttons
        toolbar_layout = QHBoxLayout()

        # Theme switcher
        theme_label = QLabel("Theme:")
        toolbar_layout.addWidget(theme_label)

        self._theme_switcher = QComboBox()
        self._theme_switcher.addItems(["Light", "Dark", "Match System"])
        self._theme_switcher.setObjectName("themeSwitcher")
        self._theme_switcher.setToolTip("Select application theme")
        self._theme_switcher.currentTextChanged.connect(self._on_theme_changed)

        # Set current theme
        current_pref = get_theme_preference()
        if current_pref == "light":
            self._theme_switcher.setCurrentText("Light")
        elif current_pref == "dark":
            self._theme_switcher.setCurrentText("Dark")
        else:
            self._theme_switcher.setCurrentText("Match System")

        toolbar_layout.addWidget(self._theme_switcher)
        toolbar_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        toolbar_layout.addWidget(refresh_btn)

        cleanup_btn = QPushButton("Clean Up")
        cleanup_btn.setToolTip("Remove completed and failed runs")
        cleanup_btn.clicked.connect(self._cleanup_runs)
        toolbar_layout.addWidget(cleanup_btn)

        layout.addLayout(toolbar_layout)

        # Splitter: sidebar | stack
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: ticket sidebar
        self._sidebar = TicketSidebarWidget()
        self._sidebar.setMinimumWidth(200)
        self._sidebar.setMaximumWidth(400)
        self._sidebar.ticket_selected.connect(self._on_ticket_selected)
        self._sidebar.create_ticket_clicked.connect(self._on_create_ticket)
        splitter.addWidget(self._sidebar)

        # Right: stacked widget (page 0 = runs table, page 1 = ticket detail)
        self._stack = QStackedWidget()

        # Page 0: runs table
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

        self._stack.addWidget(self._table)  # index 0

        # Page 1: ticket detail
        self._detail = TicketDetailWidget()
        self._detail.back_clicked.connect(self._on_ticket_back)
        self._detail.ticket_saved.connect(self._on_ticket_saved)
        self._detail.ticket_created.connect(self._on_ticket_created)
        self._detail.ticket_deleted.connect(self._on_ticket_deleted)
        self._detail.run_pid_changed.connect(self._on_run_pid_changed)
        self._stack.addWidget(self._detail)  # index 1

        splitter.addWidget(self._stack)

        # Set initial sizes: ~280px sidebar, rest for stack
        splitter.setSizes([280, 720])

        layout.addWidget(splitter)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

    def _start_refresh_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(REFRESH_INTERVAL_MS)

    def _refresh(self) -> None:
        """Reload runs from DB and update the table + ticket list."""
        self._state_manager.mark_dead_runs()
        self._runs = self._state_manager.list_runs()
        self._update_table()
        self._refresh_tickets()
        self._update_status_bar()
        self._check_gui_run_checkpoints()

    def _refresh_tickets(self) -> None:
        """Reload ticket list from disk. Skip if detail widget has unsaved edits."""
        if self._detail.is_dirty:
            return
        if self._project_path is None:
            return

        from levelup.core.tickets import read_tickets

        tickets = read_tickets(self._project_path, self._tickets_file)
        self._sidebar.set_tickets(tickets)
        self._cached_tickets = tickets

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

        ticket_count = len(getattr(self, "_cached_tickets", []))
        parts = [
            f"{active} active, {awaiting} awaiting input",
            f"{len(self._runs)} total runs",
        ]
        if ticket_count:
            parts.append(f"{ticket_count} tickets")
        self._status_bar.showMessage("  |  ".join(parts))

    # -- Ticket slots -------------------------------------------------------

    def _on_ticket_selected(self, number: int) -> None:
        """Load the selected ticket into the detail widget."""
        tickets = getattr(self, "_cached_tickets", [])
        for t in tickets:
            if t.number == number:
                self._detail.set_ticket(t)
                # Pass project context + state manager so the terminal can run
                if self._project_path is not None:
                    self._detail.set_project_context(
                        str(self._project_path),
                        self._db_path,
                        state_manager=self._state_manager,
                    )
                self._stack.setCurrentIndex(1)
                return

    def _on_theme_changed(self, theme_text: str) -> None:
        """Handle theme switcher selection change."""
        # Map UI text to preference value
        preference_map = {
            "Light": "light",
            "Dark": "dark",
            "Match System": "system",
        }
        preference = preference_map.get(theme_text, "system")

        # Save preference
        set_theme_preference(preference, project_path=self._project_path)

        # Apply theme
        actual_theme = get_current_theme(preference)
        app = QApplication.instance()
        if app:
            apply_theme(app, actual_theme)

    def _on_ticket_back(self) -> None:
        """Return to the runs table view."""
        self._stack.setCurrentIndex(0)
        self._sidebar.clear_selection()

    def _on_create_ticket(self) -> None:
        """Open the detail widget in create mode."""
        if self._project_path is None:
            return
        self._sidebar.clear_selection()
        self._detail.set_create_mode()
        self._stack.setCurrentIndex(1)

    def _on_ticket_created(self, title: str, description: str) -> None:
        """Persist a newly created ticket and show it."""
        if self._project_path is None:
            return

        from levelup.core.tickets import add_ticket

        try:
            ticket = add_ticket(
                self._project_path,
                title,
                description=description,
                filename=self._tickets_file,
            )
        except Exception as e:
            QMessageBox.critical(self, "Create Error", f"Failed to create ticket: {e}")
            return

        self._refresh_tickets()
        self._detail.set_ticket(ticket)
        if self._project_path is not None:
            self._detail.set_project_context(
                str(self._project_path),
                self._db_path,
                state_manager=self._state_manager,
            )

    def _on_ticket_saved(self, number: int, title: str, description: str) -> None:
        """Persist ticket edits to the markdown file."""
        if self._project_path is None:
            return

        from levelup.core.tickets import update_ticket

        try:
            update_ticket(
                self._project_path,
                number,
                title=title,
                description=description,
                filename=self._tickets_file,
            )
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save ticket: {e}")
            return

        self._refresh_tickets()
        # Reload the ticket in the detail view with updated data
        tickets = getattr(self, "_cached_tickets", [])
        for t in tickets:
            if t.number == number:
                self._detail.set_ticket(t)
                break

    def _on_ticket_deleted(self, number: int) -> None:
        """Delete a ticket, cleaning up any associated run and worktree."""
        if self._project_path is None:
            return

        # Clean up associated run + worktree if one exists
        run_id = self._detail.terminal.last_run_id
        if run_id:
            import shutil

            worktree_path = Path.home() / ".levelup" / "worktrees" / run_id
            if worktree_path.exists():
                try:
                    import git

                    repo = git.Repo(str(self._project_path))
                    repo.git.worktree("remove", str(worktree_path), "--force")
                except Exception:
                    try:
                        shutil.rmtree(worktree_path)
                    except Exception:
                        pass

            try:
                self._state_manager.delete_run(run_id)
            except Exception:
                pass

        # Delete the ticket from the markdown file
        from levelup.core.tickets import delete_ticket

        try:
            delete_ticket(self._project_path, number, filename=self._tickets_file)
        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Failed to delete ticket: {e}")
            return

        # Navigate back and refresh
        self._refresh_tickets()
        self._stack.setCurrentIndex(0)
        self._sidebar.clear_selection()

    # -- Run PID tracking ---------------------------------------------------

    def _on_run_pid_changed(self, pid: int, active: bool) -> None:
        """Track PIDs of GUI-spawned pipeline runs."""
        if active:
            self._active_run_pids.add(pid)
        else:
            # Process finished — remove all PIDs that are no longer alive
            self._active_run_pids.discard(pid)

    def _check_gui_run_checkpoints(self) -> None:
        """Auto-open checkpoint dialogs for GUI-spawned runs."""
        if not self._active_run_pids or self._checkpoint_dialog_open:
            return

        pending = self._state_manager.get_pending_checkpoints()
        for cp in pending:
            # Find the matching run to check its PID
            for run in self._runs:
                if run.run_id == cp.run_id and run.pid in self._active_run_pids:
                    self._checkpoint_dialog_open = True
                    dialog = CheckpointDialog(cp, self._state_manager, parent=self)
                    dialog.exec()
                    self._checkpoint_dialog_open = False
                    self._refresh()
                    return  # Handle one at a time

    # -- Run slots ----------------------------------------------------------

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

        if run.status in ("failed", "aborted", "paused"):
            resume_action = QAction("Resume", self)
            resume_action.triggered.connect(lambda: self._resume_run(run))
            menu.addAction(resume_action)

        if run.status in ("completed", "failed", "aborted", "paused"):
            remove_action = QAction("Forget", self)
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

    def _resume_run(self, run: RunRecord) -> None:
        """Show instructions for resuming a run from the CLI."""
        project = run.project_path
        QMessageBox.information(
            self,
            "Resume Run",
            f"To resume this run, use the CLI:\n\n"
            f"  levelup resume {run.run_id} --path \"{project}\"\n\n"
            f"Or select the matching ticket and use the Resume button in the terminal.",
        )

    def _remove_run(self, run: RunRecord) -> None:
        """Remove a completed/failed/aborted run from the DB."""
        reply = QMessageBox.question(
            self,
            "Forget Run",
            f"Delete run '{run.run_id[:12]}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._state_manager.delete_run(run.run_id)
        self._refresh()

    def _cleanup_runs(self) -> None:
        """Remove all completed, failed, and aborted runs."""
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
