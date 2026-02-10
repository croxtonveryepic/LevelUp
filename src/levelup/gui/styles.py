"""Dark theme stylesheet and style constants for the GUI."""

from __future__ import annotations

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #1E1E2E;
    color: #CDD6F4;
}
QTableWidget {
    background-color: #181825;
    color: #CDD6F4;
    gridline-color: #313244;
    border: 1px solid #313244;
    selection-background-color: #45475A;
    selection-color: #CDD6F4;
}
QTableWidget::item {
    padding: 6px;
}
QHeaderView::section {
    background-color: #313244;
    color: #CDD6F4;
    padding: 6px;
    border: 1px solid #45475A;
    font-weight: bold;
}
QPushButton {
    background-color: #45475A;
    color: #CDD6F4;
    border: 1px solid #585B70;
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #585B70;
}
QPushButton:pressed {
    background-color: #6C7086;
}
QPushButton#approveBtn {
    background-color: #2ECC71;
    color: #1E1E2E;
}
QPushButton#approveBtn:hover {
    background-color: #27AE60;
}
QPushButton#reviseBtn {
    background-color: #E6A817;
    color: #1E1E2E;
}
QPushButton#reviseBtn:hover {
    background-color: #D4960F;
}
QPushButton#rejectBtn {
    background-color: #E74C3C;
    color: #FFFFFF;
}
QPushButton#rejectBtn:hover {
    background-color: #C0392B;
}
QTextEdit, QPlainTextEdit {
    background-color: #181825;
    color: #CDD6F4;
    border: 1px solid #313244;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
}
QLabel {
    color: #CDD6F4;
}
QStatusBar {
    background-color: #181825;
    color: #A6ADC8;
}
QMenu {
    background-color: #313244;
    color: #CDD6F4;
    border: 1px solid #45475A;
}
QMenu::item:selected {
    background-color: #45475A;
}
QMessageBox {
    background-color: #1E1E2E;
    color: #CDD6F4;
}
QSplitter::handle {
    background-color: #313244;
    width: 2px;
}
QListWidget {
    background-color: #181825;
    color: #CDD6F4;
    border: 1px solid #313244;
    outline: none;
}
QListWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #313244;
}
QListWidget::item:selected {
    background-color: #45475A;
    color: #CDD6F4;
}
QListWidget::item:hover {
    background-color: #313244;
}
QLineEdit {
    background-color: #181825;
    color: #CDD6F4;
    border: 1px solid #313244;
    padding: 6px;
    font-size: 14px;
}
QPushButton#saveBtn {
    background-color: #2ECC71;
    color: #1E1E2E;
}
QPushButton#saveBtn:hover {
    background-color: #27AE60;
}
QPushButton#saveBtn:disabled {
    background-color: #45475A;
    color: #6C7086;
}
QPushButton#addTicketBtn {
    background-color: #2ECC71;
    color: #1E1E2E;
    border: none;
    border-radius: 4px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    font-size: 18px;
    font-weight: bold;
}
QPushButton#addTicketBtn:hover {
    background-color: #27AE60;
}
QPushButton#backBtn {
    background-color: transparent;
    border: none;
    color: #89B4FA;
    min-width: 40px;
    padding: 4px 8px;
}
QPushButton#backBtn:hover {
    color: #B4D0FB;
}
QPushButton#runBtn {
    background-color: #2ECC71;
    color: #1E1E2E;
}
QPushButton#runBtn:hover {
    background-color: #27AE60;
}
QPushButton#runBtn:disabled {
    background-color: #45475A;
    color: #6C7086;
}
QPushButton#terminateBtn {
    background-color: #E74C3C;
    color: #FFFFFF;
}
QPushButton#terminateBtn:hover {
    background-color: #C0392B;
}
QPushButton#terminateBtn:disabled {
    background-color: #45475A;
    color: #6C7086;
}
QPushButton#pauseBtn {
    background-color: #F5A623;
    color: #1E1E2E;
}
QPushButton#pauseBtn:hover {
    background-color: #E6971A;
}
QPushButton#pauseBtn:disabled {
    background-color: #45475A;
    color: #6C7086;
}
QPushButton#resumeBtn {
    background-color: #4A90D9;
    color: #FFFFFF;
}
QPushButton#resumeBtn:hover {
    background-color: #3A7BC8;
}
QPushButton#resumeBtn:disabled {
    background-color: #45475A;
    color: #6C7086;
}
QPushButton#forgetBtn {
    background-color: #6C7086;
    color: #CDD6F4;
}
QPushButton#forgetBtn:hover {
    background-color: #585B70;
}
QPushButton#forgetBtn:disabled {
    background-color: #45475A;
    color: #6C7086;
}
QPushButton#deleteBtn {
    background-color: #E74C3C;
    color: #FFFFFF;
}
QPushButton#deleteBtn:hover {
    background-color: #C0392B;
}
QPushButton#deleteBtn:disabled {
    background-color: #45475A;
    color: #6C7086;
}
QLabel#terminalStatusLabel {
    color: #A6ADC8;
    font-size: 12px;
}
"""

MONOSPACE_FONT = "Consolas"
MONOSPACE_FONT_SIZE = 13
