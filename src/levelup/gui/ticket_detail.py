"""Detail/edit widget for a single ticket."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
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

    def __init__(self, parent: QWidget | None = None, theme: str = "dark") -> None:
        super().__init__(parent)
        self._ticket: Ticket | None = None
        self._dirty = False
        self._create_mode = False
        self._project_path: str | None = None
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

        # -- Bottom: run terminal --
        self._terminal = RunTerminalWidget()
        self._terminal.run_started.connect(self._on_run_started)
        self._terminal.run_finished.connect(self._on_run_finished)
        splitter.addWidget(self._terminal)

        # Initial sizes: ~60% form, ~40% terminal
        splitter.setSizes([350, 250])

        layout.addWidget(splitter)

    # -- Public API ---------------------------------------------------------

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    @property
    def terminal(self) -> RunTerminalWidget:
        return self._terminal

    def set_project_context(
        self,
        project_path: str,
        db_path: str,
        state_manager: object | None = None,
    ) -> None:
        """Store project context so runs can be launched."""
        self._project_path = project_path
        self._db_path = db_path
        self._terminal.set_context(project_path, db_path)
        if state_manager is not None:
            self._terminal.set_state_manager(state_manager)
        # Enable run button if a ticket is loaded
        self._terminal.enable_run(self._ticket is not None)

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

        self._dirty = False
        self._save_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        self._terminal.enable_run(False)
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

        self._dirty = False
        self._save_btn.setEnabled(False)
        self._delete_btn.setEnabled(True)

        # Store ticket number for the terminal and enable Run if we have context
        self._terminal._ticket_number = ticket.number
        self._terminal.enable_run(
            self._project_path is not None and not self._terminal.is_running
        )

        # Wire existing run from DB for this ticket
        self._wire_existing_run(ticket.number)

    # -- Internal -----------------------------------------------------------

    def _wire_existing_run(self, ticket_number: int) -> None:
        """Query the DB for an existing run for this ticket and update terminal state."""
        if not self._project_path or not self._terminal._state_manager:
            return
        from levelup.state.manager import StateManager

        sm = self._terminal._state_manager
        assert isinstance(sm, StateManager)
        record = sm.get_run_for_ticket(self._project_path, ticket_number)
        if record is None:
            self._terminal._last_run_id = None
            self._terminal._update_button_states()
            self._terminal._status_label.setText("Ready")
            return

        self._terminal._last_run_id = record.run_id

        if record.status in ("completed", "failed", "aborted"):
            self._terminal._status_label.setText(f"Last run: {record.status}")
        elif record.status == "paused":
            self._terminal._status_label.setText("Paused")
        elif record.status in ("running", "pending", "waiting_for_input"):
            self._terminal._status_label.setText(f"Active ({record.status})")

        self._terminal._update_button_states()

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
        if self._terminal.is_running:
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
            self._terminal._on_terminate_clicked()

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

    def _on_run_started(self, pid: int) -> None:
        self.run_pid_changed.emit(pid, True)

    def _on_run_finished(self, exit_code: int) -> None:
        pid = 0  # Process is already gone
        self.run_pid_changed.emit(pid, False)
