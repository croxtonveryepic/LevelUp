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
"""

MONOSPACE_FONT = "Consolas"
MONOSPACE_FONT_SIZE = 13
