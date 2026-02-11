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
from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
from levelup.gui.docs_widget import DocsWidget
from levelup.gui.resources import STATUS_COLORS, STATUS_LABELS, get_status_color, status_display
from levelup.gui.ticket_detail import TicketDetailWidget
from levelup.gui.ticket_sidebar import TicketSidebarWidget
from levelup.gui.theme_manager import get_current_theme, apply_theme, set_theme_preference, get_theme_preference
from levelup.state.manager import StateManager
from levelup.state.models import RunRecord

REFRESH_INTERVAL_MS = 2000
COLUMNS = ["Run ID", "Task", "Project", "Status", "Tokens", "Step", "Started"]


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
        self._cached_tickets: list = []

        # Load tickets_file setting if we have a project path
        if project_path is not None:
            try:
                from levelup.config.loader import load_settings

                settings = load_settings(project_path=project_path)
                self._tickets_file = settings.project.tickets_file
            except Exception:
                pass

        self._current_theme = get_current_theme()

        self.setWindowTitle("LevelUp Dashboard")
        self.setMinimumSize(1000, 550)
        self._build_ui()

        # Load tickets initially if we have a project path
        if self._project_path is not None:
            from levelup.core.tickets import read_tickets
            try:
                self._cached_tickets = read_tickets(self._project_path, self._tickets_file)
                self._sidebar.set_tickets(self._cached_tickets)
            except Exception:
                pass

        self._start_refresh_timer()
        self._refresh()
        self.show()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Toolbar buttons
        toolbar_layout = QHBoxLayout()

        # Theme switcher button
        self._theme_switcher = QPushButton()
        self._theme_switcher.setObjectName("themeBtn")
        self._theme_switcher.clicked.connect(self._cycle_theme)

        # Initialize button display based on current theme preference
        self._current_theme_preference = get_theme_preference()
        self._update_theme_button()

        toolbar_layout.addWidget(self._theme_switcher)

        self._docs_btn = QPushButton("\U0001F4C4")
        self._docs_btn.setObjectName("docsBtn")
        self._docs_btn.setToolTip("Documentation")
        self._docs_btn.clicked.connect(self._on_docs_clicked)
        toolbar_layout.addWidget(self._docs_btn)

        self._completed_btn = QPushButton("\u2713")
        self._completed_btn.setObjectName("completedTicketsBtn")
        self._completed_btn.setToolTip("Completed Tickets")
        self._completed_btn.clicked.connect(self._on_completed_clicked)
        toolbar_layout.addWidget(self._completed_btn)

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
        self._sidebar = TicketSidebarWidget(theme=self._current_theme)
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
        self._detail = TicketDetailWidget(theme=self._current_theme)
        self._detail.back_clicked.connect(self._on_ticket_back)
        self._detail.ticket_saved.connect(self._on_ticket_saved)
        self._detail.ticket_created.connect(self._on_ticket_created)
        self._detail.ticket_deleted.connect(self._on_ticket_deleted)
        self._detail.run_pid_changed.connect(self._on_run_pid_changed)
        self._stack.addWidget(self._detail)  # index 1

        # Page 2: documentation viewer
        self._docs = DocsWidget(theme=self._current_theme)
        self._docs.back_clicked.connect(self._on_docs_back)
        self._stack.addWidget(self._docs)  # index 2

        # Page 3: completed tickets viewer
        self._completed = CompletedTicketsWidget(theme=self._current_theme)
        self._completed.back_clicked.connect(self._on_completed_back)
        self._completed.ticket_selected.connect(self._on_completed_ticket_selected)
        self._stack.addWidget(self._completed)  # index 3

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

        # Create run status mapping for active runs
        run_status_map: dict[int, str] = {}
        for run in self._runs:
            # Only include active run statuses (running or waiting_for_input)
            if run.ticket_number and run.status in ("running", "waiting_for_input"):
                run_status_map[run.ticket_number] = run.status

        self._sidebar.set_tickets(tickets, run_status_map=run_status_map)
        self._cached_tickets = tickets

        # Also update completed tickets page if it's currently being viewed
        if self._stack.currentIndex() == 3:  # Completed tickets page
            self._completed.set_tickets(tickets, run_status_map=run_status_map)

    def _update_table(self) -> None:
        self._table.setRowCount(len(self._runs))

        for row, run in enumerate(self._runs):
            self._table.setItem(row, 0, QTableWidgetItem(run.run_id[:12]))
            self._table.setItem(row, 1, QTableWidgetItem(run.task_title))
            self._table.setItem(row, 2, QTableWidgetItem(run.project_path))

            # Status cell with color
            status_item = QTableWidgetItem(status_display(run.status))
            color = get_status_color(run.status, theme=self._current_theme)
            status_item.setForeground(QColor(color))
            self._table.setItem(row, 3, status_item)

            # Tokens cell - format as "total (in / out)" or "N/A" if no tokens
            total_tokens = run.input_tokens + run.output_tokens
            if total_tokens > 0:
                tokens_text = f"{total_tokens:,} ({run.input_tokens:,} / {run.output_tokens:,})"
            else:
                tokens_text = "N/A"
            self._table.setItem(row, 4, QTableWidgetItem(tokens_text))

            self._table.setItem(row, 5, QTableWidgetItem(run.current_step or ""))
            self._table.setItem(row, 6, QTableWidgetItem(run.started_at[:19]))

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

    def _cycle_theme(self) -> None:
        """Cycle through theme preferences: system → light → dark → system."""
        try:
            # Cycle order: system → light → dark → system
            if self._current_theme_preference == "system":
                new_preference = "light"
            elif self._current_theme_preference == "light":
                new_preference = "dark"
            else:  # dark
                new_preference = "system"

            self._current_theme_preference = new_preference

            # Save preference
            set_theme_preference(new_preference, project_path=self._project_path)

            # Apply theme
            actual_theme = get_current_theme(new_preference)
            app = QApplication.instance()
            if app:
                apply_theme(app, actual_theme)

            # Track current theme for status color lookups
            self._current_theme = actual_theme

            # Update button appearance
            self._update_theme_button()

            # Propagate theme to all child widgets
            self._sidebar.update_theme(actual_theme)
            self._detail.update_theme(actual_theme)
            self._docs.update_theme(actual_theme)
            self._completed.update_theme(actual_theme)

            # Re-render the runs table with correct status colors
            self._update_table()
        except Exception:
            # Handle errors gracefully - theme may fail to save or apply
            # but we shouldn't crash the app
            pass

    def _update_theme_button(self) -> None:
        """Update theme button text and tooltip based on current preference."""
        symbols = {
            "system": "◐",
            "light": "☀",
            "dark": "☾"
        }
        tooltips = {
            "system": "Theme: Match System",
            "light": "Theme: Light",
            "dark": "Theme: Dark"
        }

        self._theme_switcher.setText(symbols[self._current_theme_preference])
        self._theme_switcher.setToolTip(tooltips[self._current_theme_preference])

    def _on_ticket_back(self) -> None:
        """Return to the runs table view."""
        self._stack.setCurrentIndex(0)
        self._sidebar.clear_selection()

    def _on_docs_clicked(self) -> None:
        """Switch to the documentation viewer."""
        self._sidebar.clear_selection()
        self._docs.set_project_path(self._project_path)
        self._stack.setCurrentIndex(2)

    def _on_docs_back(self) -> None:
        """Return from docs to the runs table view."""
        self._stack.setCurrentIndex(0)

    def _on_completed_clicked(self) -> None:
        """Switch to the completed tickets viewer."""
        self._sidebar.clear_selection()
        # Ensure tickets are loaded before showing completed page
        if self._project_path is not None and not hasattr(self, "_cached_tickets"):
            from levelup.core.tickets import read_tickets
            self._cached_tickets = read_tickets(self._project_path, self._tickets_file)

        # Refresh completed tickets with current ticket list
        tickets = getattr(self, "_cached_tickets", [])
        run_status_map: dict[int, str] = {}
        for run in self._runs:
            if run.ticket_number and run.status in ("running", "waiting_for_input"):
                run_status_map[run.ticket_number] = run.status
        self._completed.set_tickets(tickets, run_status_map=run_status_map)
        self._stack.setCurrentIndex(3)

    def _on_completed_back(self) -> None:
        """Return from completed tickets to the runs table view."""
        self._stack.setCurrentIndex(0)

    def _on_completed_ticket_selected(self, number: int) -> None:
        """Navigate to ticket detail from completed tickets page."""
        tickets = getattr(self, "_cached_tickets", [])
        for t in tickets:
            if t.number == number:
                self._detail.set_ticket(t)
                if self._project_path is not None:
                    self._detail.set_project_context(
                        str(self._project_path),
                        self._db_path,
                        state_manager=self._state_manager,
                    )
                self._stack.setCurrentIndex(1)
                return

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

    def _on_ticket_saved(self, number: int, title: str, description: str, metadata_json: str = "") -> None:
        """Persist ticket edits to the markdown file."""
        if self._project_path is None:
            return

        import json
        from levelup.core.tickets import update_ticket

        metadata = json.loads(metadata_json) if metadata_json else None

        try:
            update_ticket(
                self._project_path,
                number,
                title=title,
                description=description,
                metadata=metadata,
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
        terminal = self._detail.terminal
        run_id = terminal.last_run_id if terminal else None
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
        # Format token information
        total_tokens = run.input_tokens + run.output_tokens
        if total_tokens > 0:
            tokens_info = f"{total_tokens:,} ({run.input_tokens:,} in / {run.output_tokens:,} out)"
        else:
            tokens_info = "N/A"

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
            f"Tokens: {tokens_info}\n"
            f"Cost: ${run.total_cost_usd:.4f}\n"
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

    def closeEvent(self, event: object) -> None:
        """Clean up all PTY shells before closing."""
        self._detail.cleanup_all_terminals()
        super().closeEvent(event)  # type: ignore[arg-type]
