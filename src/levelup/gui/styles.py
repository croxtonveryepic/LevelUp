"""Dark and light theme stylesheets and style constants for the GUI."""

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
QPushButton#themeBtn {
    background-color: #45475A;
    color: #CDD6F4;
    border: 1px solid #585B70;
    border-radius: 4px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    font-size: 16px;
}
QPushButton#themeBtn:hover {
    background-color: #585B70;
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
QPushButton#docsBtn {
    background-color: #45475A;
    color: #CDD6F4;
    border: 1px solid #585B70;
    border-radius: 4px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    font-size: 16px;
}
QPushButton#docsBtn:hover {
    background-color: #585B70;
}
QComboBox {
    background-color: #181825;
    color: #CDD6F4;
    border: 1px solid #313244;
    border-radius: 4px;
    padding: 4px 8px;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #CDD6F4;
    border: 1px solid #45475A;
    selection-background-color: #45475A;
}
QTextBrowser#docsBrowser {
    background-color: #181825;
    color: #CDD6F4;
    border: 1px solid #313244;
    font-family: -apple-system, "Segoe UI", sans-serif;
    font-size: 14px;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog {
    background-color: #F5F5F5;
    color: #2E3440;
}
QTableWidget {
    background-color: #FFFFFF;
    color: #2E3440;
    gridline-color: #D8DEE9;
    border: 1px solid #D8DEE9;
    selection-background-color: #88C0D0;
    selection-color: #2E3440;
}
QTableWidget::item {
    padding: 6px;
}
QHeaderView::section {
    background-color: #E5E9F0;
    color: #2E3440;
    padding: 6px;
    border: 1px solid #D8DEE9;
    font-weight: bold;
}
QPushButton {
    background-color: #E5E9F0;
    color: #2E3440;
    border: 1px solid #D8DEE9;
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #D8DEE9;
}
QPushButton:pressed {
    background-color: #C0C8D8;
}
QPushButton#approveBtn {
    background-color: #27AE60;
    color: #FFFFFF;
}
QPushButton#approveBtn:hover {
    background-color: #229954;
}
QPushButton#reviseBtn {
    background-color: #F39C12;
    color: #FFFFFF;
}
QPushButton#reviseBtn:hover {
    background-color: #D68910;
}
QPushButton#rejectBtn {
    background-color: #E74C3C;
    color: #FFFFFF;
}
QPushButton#rejectBtn:hover {
    background-color: #C0392B;
}
QTextEdit, QPlainTextEdit {
    background-color: #FFFFFF;
    color: #2E3440;
    border: 1px solid #D8DEE9;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
}
QLabel {
    color: #2E3440;
}
QStatusBar {
    background-color: #ECEFF4;
    color: #4C566A;
}
QMenu {
    background-color: #FFFFFF;
    color: #2E3440;
    border: 1px solid #D8DEE9;
}
QMenu::item:selected {
    background-color: #E5E9F0;
}
QMessageBox {
    background-color: #F5F5F5;
    color: #2E3440;
}
QSplitter::handle {
    background-color: #D8DEE9;
    width: 2px;
}
QListWidget {
    background-color: #FFFFFF;
    color: #2E3440;
    border: 1px solid #D8DEE9;
    outline: none;
}
QListWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #E5E9F0;
}
QListWidget::item:selected {
    background-color: #88C0D0;
    color: #2E3440;
}
QListWidget::item:hover {
    background-color: #E5E9F0;
}
QLineEdit {
    background-color: #FFFFFF;
    color: #2E3440;
    border: 1px solid #D8DEE9;
    padding: 6px;
    font-size: 14px;
}
QPushButton#saveBtn {
    background-color: #27AE60;
    color: #FFFFFF;
}
QPushButton#saveBtn:hover {
    background-color: #229954;
}
QPushButton#saveBtn:disabled {
    background-color: #E5E9F0;
    color: #A0A8B8;
}
QPushButton#addTicketBtn {
    background-color: #27AE60;
    color: #FFFFFF;
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
    background-color: #229954;
}
QPushButton#themeBtn {
    background-color: #E5E9F0;
    color: #2E3440;
    border: 1px solid #D8DEE9;
    border-radius: 4px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    font-size: 16px;
}
QPushButton#themeBtn:hover {
    background-color: #D8DEE9;
}
QPushButton#backBtn {
    background-color: transparent;
    border: none;
    color: #5E81AC;
    min-width: 40px;
    padding: 4px 8px;
}
QPushButton#backBtn:hover {
    color: #81A1C1;
}
QPushButton#runBtn {
    background-color: #27AE60;
    color: #FFFFFF;
}
QPushButton#runBtn:hover {
    background-color: #229954;
}
QPushButton#runBtn:disabled {
    background-color: #E5E9F0;
    color: #A0A8B8;
}
QPushButton#terminateBtn {
    background-color: #E74C3C;
    color: #FFFFFF;
}
QPushButton#terminateBtn:hover {
    background-color: #C0392B;
}
QPushButton#terminateBtn:disabled {
    background-color: #E5E9F0;
    color: #A0A8B8;
}
QPushButton#pauseBtn {
    background-color: #F39C12;
    color: #FFFFFF;
}
QPushButton#pauseBtn:hover {
    background-color: #D68910;
}
QPushButton#pauseBtn:disabled {
    background-color: #E5E9F0;
    color: #A0A8B8;
}
QPushButton#resumeBtn {
    background-color: #3498DB;
    color: #FFFFFF;
}
QPushButton#resumeBtn:hover {
    background-color: #2980B9;
}
QPushButton#resumeBtn:disabled {
    background-color: #E5E9F0;
    color: #A0A8B8;
}
QPushButton#forgetBtn {
    background-color: #95A5A6;
    color: #FFFFFF;
}
QPushButton#forgetBtn:hover {
    background-color: #7F8C8D;
}
QPushButton#forgetBtn:disabled {
    background-color: #E5E9F0;
    color: #A0A8B8;
}
QPushButton#deleteBtn {
    background-color: #E74C3C;
    color: #FFFFFF;
}
QPushButton#deleteBtn:hover {
    background-color: #C0392B;
}
QPushButton#deleteBtn:disabled {
    background-color: #E5E9F0;
    color: #A0A8B8;
}
QLabel#terminalStatusLabel {
    color: #4C566A;
    font-size: 12px;
}
QPushButton#docsBtn {
    background-color: #E5E9F0;
    color: #2E3440;
    border: 1px solid #D8DEE9;
    border-radius: 4px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    font-size: 16px;
}
QPushButton#docsBtn:hover {
    background-color: #D8DEE9;
}
QComboBox {
    background-color: #FFFFFF;
    color: #2E3440;
    border: 1px solid #D8DEE9;
    border-radius: 4px;
    padding: 4px 8px;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #2E3440;
    border: 1px solid #D8DEE9;
    selection-background-color: #88C0D0;
}
QTextBrowser#docsBrowser {
    background-color: #FFFFFF;
    color: #2E3440;
    border: 1px solid #D8DEE9;
    font-family: -apple-system, "Segoe UI", sans-serif;
    font-size: 14px;
}
"""

MONOSPACE_FONT = "Consolas"
MONOSPACE_FONT_SIZE = 13
