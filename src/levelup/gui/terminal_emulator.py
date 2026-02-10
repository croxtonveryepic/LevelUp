"""Interactive VT100 terminal emulator widget using pyte + pywinpty/ptyprocess."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import pyte
from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QClipboard, QColor, QFont, QFontMetricsF, QKeyEvent, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QScrollBar, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from PyQt6.QtGui import QPaintEvent, QResizeEvent, QMouseEvent, QWheelEvent


# ---------------------------------------------------------------------------
# Catppuccin Mocha color scheme
# ---------------------------------------------------------------------------

class CatppuccinMochaColors:
    """Map pyte color names / 256-color / truecolor hex to QColor."""

    BG = QColor("#1E1E2E")
    FG = QColor("#CDD6F4")
    CURSOR = QColor("#F5E0DC")
    SELECTION = QColor("#45475A")

    _NAMED: dict[str, str] = {
        "black": "#45475A",
        "red": "#F38BA8",
        "green": "#A6E3A1",
        "yellow": "#F9E2AF",
        "blue": "#89B4FA",
        "magenta": "#F5C2E7",
        "cyan": "#94E2D5",
        "white": "#BAC2DE",
        "brightblack": "#585B70",
        "brightred": "#F38BA8",
        "brightgreen": "#A6E3A1",
        "brightyellow": "#F9E2AF",
        "brightblue": "#89B4FA",
        "brightmagenta": "#F5C2E7",
        "brightcyan": "#94E2D5",
        "brightwhite": "#A6ADC8",
        # Pyte also uses "brown" for color index 3 (yellow equivalent)
        "brown": "#F9E2AF",
        # Light variants pyte may emit
        "lightgray": "#BAC2DE",
        "lightgrey": "#BAC2DE",
        "darkgray": "#585B70",
        "darkgrey": "#585B70",
    }

    @classmethod
    def resolve(cls, color: str, is_fg: bool = True) -> QColor:
        """Resolve a pyte color string to a QColor."""
        if color == "default" or not color:
            return cls.FG if is_fg else cls.BG
        lower = color.lower()
        if lower in cls._NAMED:
            return QColor(cls._NAMED[lower])
        # 6-digit hex (pyte uses this for 256-color and truecolor)
        if len(color) == 6:
            try:
                int(color, 16)
                return QColor(f"#{color}")
            except ValueError:
                pass
        # Already prefixed with #
        if color.startswith("#"):
            return QColor(color)
        return cls.FG if is_fg else cls.BG


# ---------------------------------------------------------------------------
# Light color scheme
# ---------------------------------------------------------------------------

class LightTerminalColors:
    """Light color scheme for terminal emulator."""

    BG = QColor("#FFFFFF")
    FG = QColor("#2E3440")
    CURSOR = QColor("#5E81AC")
    SELECTION = QColor("#88C0D0")

    _NAMED: dict[str, str] = {
        "black": "#2E3440",
        "red": "#BF616A",
        "green": "#A3BE8C",
        "yellow": "#EBCB8B",
        "blue": "#5E81AC",
        "magenta": "#B48EAD",
        "cyan": "#88C0D0",
        "white": "#E5E9F0",
        "brightblack": "#4C566A",
        "brightred": "#BF616A",
        "brightgreen": "#A3BE8C",
        "brightyellow": "#EBCB8B",
        "brightblue": "#81A1C1",
        "brightmagenta": "#B48EAD",
        "brightcyan": "#8FBCBB",
        "brightwhite": "#ECEFF4",
        "brown": "#EBCB8B",
        "lightgray": "#D8DEE9",
        "lightgrey": "#D8DEE9",
        "darkgray": "#4C566A",
        "darkgrey": "#4C566A",
    }

    @classmethod
    def resolve(cls, color: str, is_fg: bool = True) -> QColor:
        """Resolve a pyte color string to a QColor."""
        if color == "default" or not color:
            return cls.FG if is_fg else cls.BG
        lower = color.lower()
        if lower in cls._NAMED:
            return QColor(cls._NAMED[lower])
        # 6-digit hex (pyte uses this for 256-color and truecolor)
        if len(color) == 6:
            try:
                int(color, 16)
                return QColor(f"#{color}")
            except ValueError:
                pass
        # Already prefixed with #
        if color.startswith("#"):
            return QColor(color)
        return cls.FG if is_fg else cls.BG


# ---------------------------------------------------------------------------
# VT100 key mapping
# ---------------------------------------------------------------------------

_QT_KEY_TO_VT100: dict[int, bytes] = {
    Qt.Key.Key_Up: b"\x1b[A",
    Qt.Key.Key_Down: b"\x1b[B",
    Qt.Key.Key_Right: b"\x1b[C",
    Qt.Key.Key_Left: b"\x1b[D",
    Qt.Key.Key_Home: b"\x1b[H",
    Qt.Key.Key_End: b"\x1b[F",
    Qt.Key.Key_Insert: b"\x1b[2~",
    Qt.Key.Key_Delete: b"\x1b[3~",
    Qt.Key.Key_PageUp: b"\x1b[5~",
    Qt.Key.Key_PageDown: b"\x1b[6~",
    Qt.Key.Key_F1: b"\x1bOP",
    Qt.Key.Key_F2: b"\x1bOQ",
    Qt.Key.Key_F3: b"\x1bOR",
    Qt.Key.Key_F4: b"\x1bOS",
    Qt.Key.Key_F5: b"\x1b[15~",
    Qt.Key.Key_F6: b"\x1b[17~",
    Qt.Key.Key_F7: b"\x1b[18~",
    Qt.Key.Key_F8: b"\x1b[19~",
    Qt.Key.Key_F9: b"\x1b[20~",
    Qt.Key.Key_F10: b"\x1b[21~",
    Qt.Key.Key_F11: b"\x1b[23~",
    Qt.Key.Key_F12: b"\x1b[24~",
    Qt.Key.Key_Backspace: b"\x7f",
    Qt.Key.Key_Tab: b"\t",
    Qt.Key.Key_Escape: b"\x1b",
}


def qt_key_to_bytes(event: QKeyEvent) -> bytes | None:
    """Convert a Qt key event to bytes to send to the PTY."""
    key = event.key()
    mods = event.modifiers()

    # Enter / Return
    if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
        return b"\r"

    # Ctrl+key combos
    if mods & Qt.KeyboardModifier.ControlModifier:
        if key == Qt.Key.Key_C:
            return b"\x03"
        if key == Qt.Key.Key_D:
            return b"\x04"
        if key == Qt.Key.Key_Z:
            return b"\x1a"
        if key == Qt.Key.Key_L:
            return b"\x0c"
        if key == Qt.Key.Key_A:
            return b"\x01"
        if key == Qt.Key.Key_E:
            return b"\x05"
        if key == Qt.Key.Key_K:
            return b"\x0b"
        if key == Qt.Key.Key_U:
            return b"\x15"
        if key == Qt.Key.Key_W:
            return b"\x17"
        # Ctrl+letter: 1..26
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return bytes([key - Qt.Key.Key_A + 1])

    # Special keys
    if key in _QT_KEY_TO_VT100:
        return _QT_KEY_TO_VT100[key]

    # Regular text input
    text = event.text()
    if text:
        return text.encode("utf-8")

    return None


# ---------------------------------------------------------------------------
# PTY backend (cross-platform)
# ---------------------------------------------------------------------------

class _PtyReaderThread(QThread):
    """Blocking reader for PTY output, running in a separate thread."""

    data_received = pyqtSignal(bytes)
    finished_signal = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pty: object = None
        self._running = False
        self._is_windows = sys.platform == "win32"

    def set_pty(self, pty: object) -> None:
        self._pty = pty

    def run(self) -> None:
        self._running = True
        try:
            if self._is_windows:
                self._read_windows()
            else:
                self._read_unix()
        except Exception:
            pass
        finally:
            self._running = False
            self.finished_signal.emit()

    def stop(self) -> None:
        self._running = False

    def _read_windows(self) -> None:
        """Read from pywinpty PTY (returns str)."""
        import time

        while self._running:
            try:
                data = self._pty.read(blocking=False)  # type: ignore[union-attr]
                if data:
                    if isinstance(data, str):
                        self.data_received.emit(data.encode("utf-8"))
                    else:
                        self.data_received.emit(data)
                else:
                    time.sleep(0.01)  # 10ms poll interval when no data
            except Exception:
                if not self._running:
                    break
                time.sleep(0.01)

    def _read_unix(self) -> None:
        """Read from ptyprocess PTY (returns bytes)."""
        while self._running:
            try:
                data = self._pty.read(4096)  # type: ignore[union-attr]
                if data:
                    if isinstance(data, str):
                        self.data_received.emit(data.encode("utf-8"))
                    else:
                        self.data_received.emit(data)
                elif data == b"":
                    break
            except EOFError:
                break
            except Exception:
                if not self._running:
                    break


class PtyBackend(QObject):
    """Cross-platform pseudo-terminal backend."""

    data_received = pyqtSignal(bytes)
    process_exited = pyqtSignal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pty: object = None
        self._reader: _PtyReaderThread | None = None
        self._is_windows = sys.platform == "win32"

    def start(self, cols: int, rows: int, cwd: str | None = None, env: dict[str, str] | None = None) -> None:
        """Spawn a shell in a PTY."""
        spawn_env = dict(os.environ)
        spawn_env["TERM"] = "xterm-256color"
        spawn_env.pop("NO_COLOR", None)
        if env:
            spawn_env.update(env)

        if self._is_windows:
            self._start_windows(cols, rows, cwd, spawn_env)
        else:
            self._start_unix(cols, rows, cwd, spawn_env)

        self._reader = _PtyReaderThread(self)
        self._reader.set_pty(self._pty)
        self._reader.data_received.connect(self.data_received)
        self._reader.finished_signal.connect(self._on_reader_done)
        self._reader.start()

    def _start_windows(self, cols: int, rows: int, cwd: str | None, env: dict[str, str]) -> None:
        from winpty import PTY as WinPTY  # type: ignore[import-untyped]

        self._pty = WinPTY(cols, rows)
        shell = env.get("COMSPEC", "powershell.exe")
        # pywinpty expects env as a \0-separated string of KEY=VALUE pairs
        env_str = "\0".join(f"{k}={v}" for k, v in env.items()) + "\0"
        self._pty.spawn(shell, cwd=cwd, env=env_str)  # type: ignore[union-attr]
        # Force UTF-8 for PowerShell
        if "powershell" in shell.lower():
            self.write("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\r".encode("utf-8"))

    def _start_unix(self, cols: int, rows: int, cwd: str | None, env: dict[str, str]) -> None:
        from ptyprocess import PtyProcess  # type: ignore[import-untyped]

        shell = env.get("SHELL", "/bin/bash")
        self._pty = PtyProcess.spawn(
            [shell],
            dimensions=(rows, cols),
            cwd=cwd,
            env=env,
        )

    def write(self, data: bytes) -> None:
        """Write bytes to the PTY."""
        if self._pty is None:
            return
        if self._is_windows:
            self._pty.write(data.decode("utf-8", errors="replace"))  # type: ignore[union-attr]
        else:
            self._pty.write(data)  # type: ignore[union-attr]

    def resize(self, cols: int, rows: int) -> None:
        """Resize the PTY."""
        if self._pty is None:
            return
        try:
            if self._is_windows:
                self._pty.set_size(cols, rows)  # type: ignore[union-attr]
            else:
                self._pty.setwinsize(rows, cols)  # type: ignore[union-attr]
        except Exception:
            pass

    def close(self) -> None:
        """Shut down the PTY and reader thread."""
        if self._reader is not None:
            self._reader.stop()
            self._reader.wait(2000)
            self._reader = None
        if self._pty is not None:
            try:
                if self._is_windows:
                    # pywinpty PTY has no close() method; release reference for GC
                    pass
                else:
                    self._pty.terminate(force=True)  # type: ignore[union-attr]
            except Exception:
                pass
            self._pty = None

    @property
    def is_alive(self) -> bool:
        if self._pty is None:
            return False
        if self._is_windows:
            return self._pty.isalive() if hasattr(self._pty, "isalive") else True  # type: ignore[union-attr]
        return self._pty.isalive()  # type: ignore[union-attr]

    def _on_reader_done(self) -> None:
        exit_code = 0
        if self._pty is not None:
            try:
                if self._is_windows:
                    status = self._pty.get_exitstatus()  # type: ignore[union-attr]
                    exit_code = status if status is not None else 0
                else:
                    exit_code = self._pty.exitstatus or 0  # type: ignore[union-attr]
            except Exception:
                pass
        self.process_exited.emit(exit_code)


# ---------------------------------------------------------------------------
# Terminal emulator widget
# ---------------------------------------------------------------------------

class TerminalEmulatorWidget(QWidget):
    """Full VT100 terminal emulator using pyte for screen state and QPainter for rendering."""

    shell_started = pyqtSignal()
    shell_exited = pyqtSignal(int)

    def __init__(
        self,
        parent: QWidget | None = None,
        color_scheme: type[CatppuccinMochaColors] | type[LightTerminalColors] = CatppuccinMochaColors
    ) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        # Color scheme
        self._color_scheme = color_scheme

        # Font setup
        self._font = QFont("Consolas", 13)
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        fm = QFontMetricsF(self._font)
        self._cell_width = fm.horizontalAdvance("M")
        self._cell_height = fm.height()
        self._font_ascent = fm.ascent()

        # Screen dimensions (in cells)
        self._cols = 80
        self._rows = 24

        # pyte terminal state
        self._screen = pyte.HistoryScreen(self._cols, self._rows, history=10000)
        self._stream = pyte.Stream(self._screen)

        # PTY backend
        self._pty = PtyBackend(self)
        self._pty.data_received.connect(self._on_pty_data)
        self._pty.process_exited.connect(self._on_pty_exited)
        self._shell_running = False

        # Cursor blink timer
        self._cursor_visible = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._toggle_cursor)
        self._cursor_timer.start(530)

        # Selection state (cell coordinates)
        self._selection_start: tuple[int, int] | None = None  # (col, row)
        self._selection_end: tuple[int, int] | None = None
        self._selecting = False

        # Scroll offset (for history scrollback; 0 = at bottom)
        self._scroll_offset = 0

        # Scrollbar
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Dirty tracking
        self._dirty_lines: set[int] = set()
        self._full_repaint = True

    # -- Public API ---------------------------------------------------------

    def start_shell(self, cwd: str | None = None, env: dict[str, str] | None = None) -> None:
        """Start an interactive shell in the terminal."""
        if self._shell_running:
            return
        self._recalculate_grid()
        self._pty.start(self._cols, self._rows, cwd=cwd, env=env)
        self._shell_running = True
        self.shell_started.emit()

    def send_command(self, command: str) -> None:
        """Send a command string to the shell (appends \\r)."""
        if self._shell_running:
            self._pty.write((command + "\r").encode("utf-8"))

    def send_interrupt(self) -> None:
        """Send Ctrl+C to the shell."""
        if self._shell_running:
            self._pty.write(b"\x03")

    def send_clear(self) -> None:
        """Send a clear-screen command to the shell."""
        if self._shell_running:
            cmd = "cls" if sys.platform == "win32" else "clear"
            self.send_command(cmd)

    def close_shell(self) -> None:
        """Shut down the shell and PTY."""
        self._shell_running = False
        self._pty.close()

    @property
    def is_shell_running(self) -> bool:
        return self._shell_running

    def set_color_scheme(
        self, color_scheme: type[CatppuccinMochaColors] | type[LightTerminalColors]
    ) -> None:
        """Change the color scheme and trigger a repaint."""
        self._color_scheme = color_scheme
        self._full_repaint = True
        self.update()

    # -- Qt event handlers --------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setFont(self._font)

        colors = self._color_scheme
        cw = self._cell_width
        ch = self._cell_height
        ascent = self._font_ascent

        # Fill background
        painter.fillRect(self.rect(), colors.BG)

        screen = self._screen

        # Determine selection range in normalized form
        sel_start, sel_end = self._normalized_selection()

        for row in range(self._rows):
            y = row * ch
            line = screen.buffer[row]
            for col in range(self._cols):
                x = col * cw

                char = line[col]
                ch_data = char.data if char.data else " "
                fg = colors.resolve(char.fg, is_fg=True) if char.fg else colors.FG
                bg = colors.resolve(char.bg, is_fg=False) if char.bg else colors.BG

                # Reverse video
                if char.reverse:
                    fg, bg = bg, fg

                # Bold brightens fg
                if char.bold and fg == colors.FG:
                    fg = QColor("#F5E0DC")

                # Selection highlight
                if sel_start is not None and sel_end is not None:
                    if self._cell_in_selection(col, row, sel_start, sel_end):
                        bg = colors.SELECTION
                        fg = colors.FG

                # Draw cell background
                if bg != colors.BG:
                    painter.fillRect(int(x), int(y), int(cw) + 1, int(ch) + 1, bg)

                # Draw character
                if ch_data != " ":
                    painter.setPen(QPen(fg))
                    painter.drawText(int(x), int(y + ascent), ch_data)

        # Draw cursor
        if self._cursor_visible and self._scroll_offset == 0:
            cx = screen.cursor.x
            cy = screen.cursor.y
            if 0 <= cx < self._cols and 0 <= cy < self._rows:
                painter.fillRect(
                    int(cx * cw), int(cy * ch),
                    int(cw), int(ch),
                    colors.CURSOR,
                )
                # Draw the character under cursor in bg color
                line = screen.buffer[cy]
                char = line[cx]
                ch_data = char.data if char.data else " "
                if ch_data != " ":
                    painter.setPen(QPen(colors.BG))
                    painter.drawText(int(cx * cw), int(cy * ch + ascent), ch_data)

        painter.end()
        self._full_repaint = False
        self._dirty_lines.clear()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._recalculate_grid()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        mods = event.modifiers()

        # Ctrl+Shift+C = copy, Ctrl+Shift+V = paste
        if mods & Qt.KeyboardModifier.ControlModifier and mods & Qt.KeyboardModifier.ShiftModifier:
            if event.key() == Qt.Key.Key_C:
                self._copy_selection()
                return
            if event.key() == Qt.Key.Key_V:
                self._paste_clipboard()
                return

        # Ctrl+C with selection = copy; without selection = interrupt
        if mods == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_C:
            if self._selection_start is not None and self._selection_end is not None:
                self._copy_selection()
                return

        # Ctrl+V = paste
        if mods == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_V:
            self._paste_clipboard()
            return

        data = qt_key_to_bytes(event)
        if data is not None:
            # Clear selection on typing
            if self._selection_start is not None:
                self._selection_start = None
                self._selection_end = None
                self.update()
            # Snap to bottom on input
            self._scroll_offset = 0
            self._pty.write(data)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            col = int(pos.x() / self._cell_width)
            row = int(pos.y() / self._cell_height)
            self._selection_start = (col, row)
            self._selection_end = None
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._selecting:
            pos = event.position()
            col = max(0, min(int(pos.x() / self._cell_width), self._cols - 1))
            row = max(0, min(int(pos.y() / self._cell_height), self._rows - 1))
            self._selection_end = (col, row)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = False
            # If no movement, clear selection
            if self._selection_end is None or self._selection_start == self._selection_end:
                self._selection_start = None
                self._selection_end = None
                self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta > 0:
            # Scroll up (into history)
            max_offset = len(self._screen.history.top)
            self._scroll_offset = min(self._scroll_offset + 3, max_offset)
        else:
            # Scroll down (toward bottom)
            self._scroll_offset = max(self._scroll_offset - 3, 0)
        self.update()

    # -- Internal -----------------------------------------------------------

    def _recalculate_grid(self) -> None:
        """Recalculate grid dimensions from widget size and resize PTY + pyte."""
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return
        new_cols = max(10, int(w / self._cell_width))
        new_rows = max(2, int(h / self._cell_height))

        if new_cols != self._cols or new_rows != self._rows:
            self._cols = new_cols
            self._rows = new_rows
            self._screen.resize(self._rows, self._cols)
            if self._shell_running:
                self._pty.resize(self._cols, self._rows)
            self._full_repaint = True
            self.update()

    def _on_pty_data(self, data: bytes) -> None:
        """Feed PTY output into pyte and trigger repaint."""
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = data.decode("latin-1", errors="replace")
        self._stream.feed(text)
        self._full_repaint = True
        self.update()

    def _on_pty_exited(self, exit_code: int) -> None:
        self._shell_running = False
        self.shell_exited.emit(exit_code)

    def _toggle_cursor(self) -> None:
        self._cursor_visible = not self._cursor_visible
        if self._scroll_offset == 0:
            # Only repaint cursor area
            cx = self._screen.cursor.x
            cy = self._screen.cursor.y
            self.update(
                int(cx * self._cell_width),
                int(cy * self._cell_height),
                int(self._cell_width) + 1,
                int(self._cell_height) + 1,
            )

    def _normalized_selection(self) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
        """Return selection start/end in top-left to bottom-right order."""
        if self._selection_start is None or self._selection_end is None:
            return None, None
        s = self._selection_start
        e = self._selection_end
        if (s[1], s[0]) > (e[1], e[0]):
            return e, s
        return s, e

    @staticmethod
    def _cell_in_selection(
        col: int,
        row: int,
        sel_start: tuple[int, int],
        sel_end: tuple[int, int],
    ) -> bool:
        """Check if (col, row) is inside the selection rectangle."""
        sc, sr = sel_start
        ec, er = sel_end
        if row < sr or row > er:
            return False
        if row == sr and row == er:
            return sc <= col <= ec
        if row == sr:
            return col >= sc
        if row == er:
            return col <= ec
        return True

    def _get_selected_text(self) -> str:
        """Extract text from the current selection."""
        sel_start, sel_end = self._normalized_selection()
        if sel_start is None or sel_end is None:
            return ""
        lines = []
        sc, sr = sel_start
        ec, er = sel_end
        for row in range(sr, er + 1):
            line = self._screen.buffer[row]
            start_col = sc if row == sr else 0
            end_col = ec if row == er else self._cols - 1
            chars = []
            for col in range(start_col, end_col + 1):
                ch = line[col].data
                chars.append(ch if ch else " ")
            lines.append("".join(chars).rstrip())
        return "\n".join(lines)

    def _copy_selection(self) -> None:
        text = self._get_selected_text()
        if text:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)

    def _paste_clipboard(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            text = clipboard.text()
            if text:
                self._pty.write(text.encode("utf-8"))


# Alias for convenience
TerminalEmulator = TerminalEmulatorWidget
