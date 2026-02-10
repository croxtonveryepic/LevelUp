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
from levelup.gui.resources import TICKET_STATUS_COLORS, TICKET_STATUS_ICONS
from levelup.gui.run_terminal import RunTerminalWidget


class TicketDetailWidget(QWidget):
    """Right-hand panel for viewing and editing a single ticket."""

    back_clicked = pyqtSignal()
    ticket_saved = pyqtSignal(int, str, str)  # number, title, description
    run_pid_changed = pyqtSignal(int, bool)   # pid, active

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ticket: Ticket | None = None
        self._dirty = False
        self._project_path: str | None = None
        self._db_path: str | None = None

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
        title_label = QLabel("Title")
        title_label.setStyleSheet("font-size: 12px; color: #A6ADC8; margin-top: 8px;")
        form_layout.addWidget(title_label)

        self._title_edit = QLineEdit()
        self._title_edit.textChanged.connect(self._mark_dirty)
        form_layout.addWidget(self._title_edit)

        # Status
        self._status_label = QLabel()
        self._status_label.setStyleSheet("font-size: 13px; margin-top: 4px;")
        form_layout.addWidget(self._status_label)

        # Description
        desc_label = QLabel("Description")
        desc_label.setStyleSheet("font-size: 12px; color: #A6ADC8; margin-top: 8px;")
        form_layout.addWidget(desc_label)

        self._desc_edit = QPlainTextEdit()
        self._desc_edit.textChanged.connect(self._mark_dirty)
        form_layout.addWidget(self._desc_edit)

        # Buttons
        btn_layout = QHBoxLayout()
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

    def set_project_context(self, project_path: str, db_path: str) -> None:
        """Store project context so runs can be launched."""
        self._project_path = project_path
        self._db_path = db_path
        self._terminal.set_context(project_path, db_path)
        # Enable run button if a ticket is loaded
        self._terminal.enable_run(self._ticket is not None)

    def set_ticket(self, ticket: Ticket) -> None:
        """Load ticket data into the form, clearing the dirty flag."""
        self._ticket = ticket
        self._number_label.setText(f"Ticket #{ticket.number}")

        self._title_edit.blockSignals(True)
        self._title_edit.setText(ticket.title)
        self._title_edit.blockSignals(False)

        icon = TICKET_STATUS_ICONS.get(ticket.status.value, "")
        color = TICKET_STATUS_COLORS.get(ticket.status.value, "#CDD6F4")
        self._status_label.setText(f"{icon} {ticket.status.value}")
        self._status_label.setStyleSheet(
            f"font-size: 13px; margin-top: 4px; color: {color};"
        )

        self._desc_edit.blockSignals(True)
        self._desc_edit.setPlainText(ticket.description)
        self._desc_edit.blockSignals(False)

        self._dirty = False
        self._save_btn.setEnabled(False)

        # Store ticket number for the terminal and enable Run if we have context
        self._terminal._ticket_number = ticket.number
        self._terminal.enable_run(
            self._project_path is not None and not self._terminal.is_running
        )

    # -- Internal -----------------------------------------------------------

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
        if self._ticket is None:
            return
        title = self._title_edit.text().replace("\n", " ").strip()
        description = self._desc_edit.toPlainText()
        self.ticket_saved.emit(self._ticket.number, title, description)
        self._dirty = False
        self._save_btn.setEnabled(False)

    def _on_run_started(self, pid: int) -> None:
        self.run_pid_changed.emit(pid, True)

    def _on_run_finished(self, exit_code: int) -> None:
        pid = 0  # Process is already gone
        self.run_pid_changed.emit(pid, False)
