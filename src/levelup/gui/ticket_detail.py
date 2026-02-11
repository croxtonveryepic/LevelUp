"""Detail/edit widget for a single ticket."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from levelup.core.tickets import Ticket
from levelup.gui.resources import TICKET_STATUS_COLORS, TICKET_STATUS_ICONS, get_ticket_status_color
from levelup.gui.run_terminal import RunTerminalWidget


class TicketDetailWidget(QWidget):
    """Right-hand panel for viewing and editing a single ticket."""

    back_clicked = pyqtSignal()
    ticket_saved = pyqtSignal(int, str, str)  # number, title, description
    ticket_created = pyqtSignal(str, str)     # title, description
    ticket_deleted = pyqtSignal(int)           # ticket number
    run_pid_changed = pyqtSignal(int, bool)   # pid, active

    def __init__(self, parent: QWidget | None = None, theme: str = "dark", project_path: str | None = None) -> None:
        super().__init__(parent)
        self._ticket: Ticket | None = None
        self._dirty = False
        self._create_mode = False
        self._project_path: str | None = project_path
        self._db_path: str | None = None
        self._current_theme = theme

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Vertical splitter: form (top) | terminal (bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # -- Top: ticket form --
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)

        # Top bar: back button + ticket number
        top_bar = QHBoxLayout()
        self._back_btn = QPushButton("\u2190 Back")
        self._back_btn.setObjectName("backBtn")
        self._back_btn.clicked.connect(self._on_back)
        top_bar.addWidget(self._back_btn)

        self._number_label = QLabel()
        self._number_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        top_bar.addWidget(self._number_label)
        top_bar.addStretch()
        form_layout.addLayout(top_bar)

        # Title
        self._title_label = QLabel("Title")
        self._title_label.setStyleSheet("font-size: 12px; margin-top: 8px;")
        form_layout.addWidget(self._title_label)

        self._title_edit = QLineEdit()
        self._title_edit.textChanged.connect(self._mark_dirty)
        form_layout.addWidget(self._title_edit)

        # Status
        self._status_label = QLabel()
        self._status_label.setStyleSheet("font-size: 13px; margin-top: 4px;")
        form_layout.addWidget(self._status_label)

        # Description
        self._desc_label = QLabel("Description")
        self._desc_label.setStyleSheet("font-size: 12px; margin-top: 8px;")
        form_layout.addWidget(self._desc_label)

        self._desc_edit = QPlainTextEdit()
        self._desc_edit.textChanged.connect(self._mark_dirty)
        form_layout.addWidget(self._desc_edit)

        # Auto-approve checkbox
        self.auto_approve_checkbox = QCheckBox("Auto-approve checkpoints")
        self.auto_approve_checkbox.setToolTip(
            "Automatically approve all checkpoints for this ticket, skipping user prompts"
        )
        self.auto_approve_checkbox.stateChanged.connect(self._mark_dirty)
        form_layout.addWidget(self.auto_approve_checkbox)

        # Buttons
        btn_layout = QHBoxLayout()

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setObjectName("deleteBtn")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._delete_btn)

        btn_layout.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        self._save_btn = QPushButton("Save")
        self._save_btn.setObjectName("saveBtn")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)

        form_layout.addLayout(btn_layout)
        splitter.addWidget(form_widget)

        # -- Bottom: per-ticket terminal stack --
        self._terminal_stack = QStackedWidget()
        self._terminals: dict[int, RunTerminalWidget] = {}
        self._current_terminal: RunTerminalWidget | None = None
        self._state_manager_ref: object | None = None
        splitter.addWidget(self._terminal_stack)

        # Initial sizes: ~60% form, ~40% terminal
        splitter.setSizes([350, 250])

        layout.addWidget(splitter)

    # -- Public API ---------------------------------------------------------

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    @property
    def terminal(self) -> RunTerminalWidget | None:
        return self._current_terminal

    def _get_or_create_terminal(self, ticket_number: int) -> RunTerminalWidget:
        """Return an existing terminal for *ticket_number*, or create one."""
        if ticket_number in self._terminals:
            return self._terminals[ticket_number]
        terminal = RunTerminalWidget()
        terminal.run_started.connect(self._on_run_started)
        terminal.run_finished.connect(self._on_run_finished)
        if self._project_path and self._db_path:
            terminal.set_context(self._project_path, self._db_path)
        if self._state_manager_ref is not None:
            terminal.set_state_manager(self._state_manager_ref)
        terminal._ticket_number = ticket_number
        self._terminal_stack.addWidget(terminal)
        self._terminals[ticket_number] = terminal
        return terminal

    def _show_terminal(self, ticket_number: int) -> None:
        """Switch the visible terminal to the one for *ticket_number*."""
        terminal = self._get_or_create_terminal(ticket_number)
        self._terminal_stack.setCurrentWidget(terminal)
        self._current_terminal = terminal

    def _remove_terminal(self, ticket_number: int) -> None:
        """Destroy the terminal associated with *ticket_number*."""
        terminal = self._terminals.pop(ticket_number, None)
        if terminal is None:
            return
        if terminal is self._current_terminal:
            self._current_terminal = None
        if terminal._shell_started:
            terminal._terminal.close_shell()
        self._terminal_stack.removeWidget(terminal)
        terminal.deleteLater()

    def cleanup_all_terminals(self) -> None:
        """Shut down every PTY and clear the terminal dict."""
        for terminal in list(self._terminals.values()):
            if terminal._shell_started:
                terminal._terminal.close_shell()
        self._terminals.clear()
        self._current_terminal = None

    def set_project_context(
        self,
        project_path: str,
        db_path: str,
        state_manager: object | None = None,
    ) -> None:
        """Store project context so runs can be launched."""
        self._project_path = project_path
        self._db_path = db_path
        if state_manager is not None:
            self._state_manager_ref = state_manager
        # Propagate context to all existing terminals
        for terminal in self._terminals.values():
            terminal.set_context(project_path, db_path)
            if state_manager is not None:
                terminal.set_state_manager(state_manager)
        # Enable run button on the current terminal if a ticket is loaded
        if self._current_terminal is not None:
            self._current_terminal.enable_run(self._ticket is not None)

    def update_theme(self, theme: str) -> None:
        """Update widget styling for theme change.

        Args:
            theme: "light" or "dark"
        """
        self._current_theme = theme
        # Update label colors
        label_color = "#4C566A" if theme == "light" else "#A6ADC8"
        self._title_label.setStyleSheet(f"font-size: 12px; margin-top: 8px; color: {label_color};")
        self._desc_label.setStyleSheet(f"font-size: 12px; margin-top: 8px; color: {label_color};")

        # Re-render status label if ticket is loaded
        if self._ticket is not None:
            icon = TICKET_STATUS_ICONS.get(self._ticket.status.value, "")
            color = get_ticket_status_color(self._ticket.status.value, theme=theme)
            self._status_label.setText(f"{icon} {self._ticket.status.value}")
            self._status_label.setStyleSheet(
                f"font-size: 13px; margin-top: 4px; color: {color};"
            )

    def set_create_mode(self) -> None:
        """Switch to create-new-ticket mode: clear fields and disable Run."""
        self._create_mode = True
        self._ticket = None

        self._number_label.setText("New Ticket")

        self._title_edit.blockSignals(True)
        self._title_edit.setText("")
        self._title_edit.blockSignals(False)

        self._status_label.hide()

        self._desc_edit.blockSignals(True)
        self._desc_edit.setPlainText("")
        self._desc_edit.blockSignals(False)

        self.auto_approve_checkbox.blockSignals(True)
        self.auto_approve_checkbox.setChecked(False)
        self.auto_approve_checkbox.blockSignals(False)

        self._dirty = False
        self._save_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        if self._current_terminal is not None:
            self._current_terminal.enable_run(False)
        self._title_edit.setFocus()

    def set_ticket(self, ticket: Ticket) -> None:
        """Load ticket data into the form, clearing the dirty flag."""
        self._create_mode = False
        self._status_label.show()
        self._ticket = ticket
        self._number_label.setText(f"Ticket #{ticket.number}")

        self._title_edit.blockSignals(True)
        self._title_edit.setText(ticket.title)
        self._title_edit.blockSignals(False)

        icon = TICKET_STATUS_ICONS.get(ticket.status.value, "")
        color = get_ticket_status_color(ticket.status.value, theme=self._current_theme)
        self._status_label.setText(f"{icon} {ticket.status.value}")
        self._status_label.setStyleSheet(
            f"font-size: 13px; margin-top: 4px; color: {color};"
        )

        self._desc_edit.blockSignals(True)
        self._desc_edit.setPlainText(ticket.description)
        self._desc_edit.blockSignals(False)

        # Load auto-approve metadata
        self.auto_approve_checkbox.blockSignals(True)
        if ticket.metadata and "auto_approve" in ticket.metadata:
            self.auto_approve_checkbox.setChecked(bool(ticket.metadata["auto_approve"]))
        else:
            self.auto_approve_checkbox.setChecked(False)
        self.auto_approve_checkbox.blockSignals(False)

        self._dirty = False
        self._save_btn.setEnabled(False)
        self._delete_btn.setEnabled(True)

        # Show (or create) the terminal for this ticket
        self._show_terminal(ticket.number)
        assert self._current_terminal is not None
        self._current_terminal.enable_run(
            self._project_path is not None and not self._current_terminal.is_running
        )

        # Wire existing run from DB for this ticket
        self._wire_existing_run(ticket.number)

    # -- Internal -----------------------------------------------------------

    def _wire_existing_run(self, ticket_number: int) -> None:
        """Query the DB for an existing run for this ticket and update terminal state."""
        if self._current_terminal is None:
            return
        if not self._project_path or not self._current_terminal._state_manager:
            return
        from levelup.state.manager import StateManager

        sm = self._current_terminal._state_manager
        assert isinstance(sm, StateManager)
        record = sm.get_run_for_ticket(self._project_path, ticket_number)
        if record is None:
            self._current_terminal._last_run_id = None
            self._current_terminal._update_button_states()
            self._current_terminal._status_label.setText("Ready")
            return

        self._current_terminal._last_run_id = record.run_id

        if record.status in ("completed", "failed", "aborted"):
            self._current_terminal._status_label.setText(f"Last run: {record.status}")
        elif record.status == "paused":
            self._current_terminal._status_label.setText("Paused")
        elif record.status in ("running", "pending", "waiting_for_input"):
            self._current_terminal._status_label.setText(f"Active ({record.status})")

        self._current_terminal._update_button_states()

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._save_btn.setEnabled(True)

    def _on_back(self) -> None:
        if self._dirty:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Discard unsaved changes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._dirty = False
        self.back_clicked.emit()

    def _on_cancel(self) -> None:
        if self._create_mode:
            if self._dirty:
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    "Discard unsaved changes?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self._create_mode = False
            self._dirty = False
            self.back_clicked.emit()
            return
        if self._ticket is not None:
            if self._dirty:
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    "Discard unsaved changes?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self.set_ticket(self._ticket)

    def _on_save(self) -> None:
        if self._create_mode:
            title = self._title_edit.text().replace("\n", " ").strip()
            if not title:
                QMessageBox.warning(self, "Validation", "Title cannot be empty.")
                return
            description = self._desc_edit.toPlainText()
            self.ticket_created.emit(title, description)
            self._dirty = False
            self._save_btn.setEnabled(False)
            return
        if self._ticket is None:
            return
        title = self._title_edit.text().replace("\n", " ").strip()
        description = self._desc_edit.toPlainText()
        self.ticket_saved.emit(self._ticket.number, title, description)
        self._dirty = False
        self._save_btn.setEnabled(False)

    def _on_delete(self) -> None:
        if self._ticket is None:
            return
        number = self._ticket.number
        title = self._ticket.title

        # If a pipeline run is active, warn and terminate first
        if self._current_terminal is not None and self._current_terminal.is_running:
            reply = QMessageBox.warning(
                self,
                "Active Run",
                f"Ticket #{number} has an active pipeline run.\n"
                "It will be terminated. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._current_terminal._on_terminate_clicked()

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Ticket",
            f"Permanently delete ticket #{number}: '{title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.ticket_deleted.emit(number)
        self._remove_terminal(number)

    def _on_run_started(self, pid: int) -> None:
        self.run_pid_changed.emit(pid, True)

    def _on_run_finished(self, exit_code: int) -> None:
        pid = 0  # Process is already gone
        self.run_pid_changed.emit(pid, False)

    # -- Helper methods for tests -------------------------------------------

    def load_ticket(self, ticket: Ticket) -> None:
        """Load a ticket into the widget (alias for set_ticket)."""
        self.set_ticket(ticket)

    def save_ticket(self) -> None:
        """Save the current ticket (programmatically trigger save).

        This method is primarily for testing. It directly updates the ticket
        file with the current form values including metadata.
        """
        if self._project_path is None:
            return

        from pathlib import Path
        from levelup.core.tickets import update_ticket

        if self._create_mode:
            # In create mode, we'd normally emit ticket_created signal
            # For testing, we'll create the ticket directly
            from levelup.core.tickets import add_ticket
            title = self._title_edit.text().replace("\n", " ").strip()
            description = self._desc_edit.toPlainText()
            metadata = None
            if self.auto_approve_checkbox.isChecked():
                metadata = {"auto_approve": True}
            add_ticket(Path(self._project_path), title, description, metadata=metadata)
        elif self._ticket is not None:
            title = self._title_edit.text().replace("\n", " ").strip()
            description = self._desc_edit.toPlainText()

            # Build metadata
            metadata = self._ticket.metadata.copy() if self._ticket.metadata else {}
            metadata["auto_approve"] = self.auto_approve_checkbox.isChecked()

            update_ticket(
                Path(self._project_path),
                self._ticket.number,
                title=title,
                description=description,
                metadata=metadata,
            )

        self._dirty = False
        self._save_btn.setEnabled(False)

    @property
    def project_path(self) -> str | None:
        """Get the current project path."""
        return self._project_path

    def set_project_path(self, path: str) -> None:
        """Set the project path for testing."""
        self._project_path = path
