"""Tests for the terminal emulator pure-logic components."""

from __future__ import annotations

import pytest

from levelup.gui.terminal_emulator import CatppuccinMochaColors, qt_key_to_bytes


# ---------------------------------------------------------------------------
# CatppuccinMochaColors
# ---------------------------------------------------------------------------

class TestCatppuccinMochaColors:
    def test_default_fg(self):
        c = CatppuccinMochaColors.resolve("default", is_fg=True)
        assert c == CatppuccinMochaColors.FG

    def test_default_bg(self):
        c = CatppuccinMochaColors.resolve("default", is_fg=False)
        assert c == CatppuccinMochaColors.BG

    def test_empty_string_fg(self):
        c = CatppuccinMochaColors.resolve("", is_fg=True)
        assert c == CatppuccinMochaColors.FG

    def test_empty_string_bg(self):
        c = CatppuccinMochaColors.resolve("", is_fg=False)
        assert c == CatppuccinMochaColors.BG

    def test_named_color_red(self):
        c = CatppuccinMochaColors.resolve("red")
        assert c.name() == "#f38ba8"

    def test_named_color_green(self):
        c = CatppuccinMochaColors.resolve("green")
        assert c.name() == "#a6e3a1"

    def test_named_color_brightblue(self):
        c = CatppuccinMochaColors.resolve("brightblue")
        assert c.name() == "#89b4fa"

    def test_named_color_case_insensitive(self):
        c = CatppuccinMochaColors.resolve("Red")
        assert c.name() == "#f38ba8"

    def test_hex_6digit(self):
        c = CatppuccinMochaColors.resolve("ff8800")
        assert c.name() == "#ff8800"

    def test_hex_with_hash(self):
        c = CatppuccinMochaColors.resolve("#abcdef")
        assert c.name() == "#abcdef"

    def test_unknown_string_returns_fg(self):
        c = CatppuccinMochaColors.resolve("notacolor", is_fg=True)
        assert c == CatppuccinMochaColors.FG

    def test_unknown_string_returns_bg(self):
        c = CatppuccinMochaColors.resolve("notacolor", is_fg=False)
        assert c == CatppuccinMochaColors.BG

    def test_brown_maps_to_yellow(self):
        c = CatppuccinMochaColors.resolve("brown")
        assert c.name() == "#f9e2af"


# ---------------------------------------------------------------------------
# Key mapping
# ---------------------------------------------------------------------------


def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestKeyMapping:
    """Test VT100 escape sequence generation."""

    def _make_key_event(self, key: int, modifiers: object | None = None, text: str = "") -> object:
        """Create a minimal QKeyEvent."""
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtWidgets import QApplication

        # Ensure QApplication exists
        app = QApplication.instance() or QApplication([])

        mods = modifiers if modifiers is not None else Qt.KeyboardModifier(0)
        return QKeyEvent(
            QEvent.Type.KeyPress,
            key,
            mods,
            text,
        )

    def test_enter_key(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_Return)
        assert qt_key_to_bytes(event) == b"\r"

    def test_arrow_up(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_Up)
        assert qt_key_to_bytes(event) == b"\x1b[A"

    def test_arrow_down(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_Down)
        assert qt_key_to_bytes(event) == b"\x1b[B"

    def test_arrow_right(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_Right)
        assert qt_key_to_bytes(event) == b"\x1b[C"

    def test_arrow_left(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_Left)
        assert qt_key_to_bytes(event) == b"\x1b[D"

    def test_backspace(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_Backspace)
        assert qt_key_to_bytes(event) == b"\x7f"

    def test_tab(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_Tab, text="\t")
        assert qt_key_to_bytes(event) == b"\t"

    def test_escape(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_Escape)
        assert qt_key_to_bytes(event) == b"\x1b"

    def test_ctrl_c(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(
            Qt.Key.Key_C,
            modifiers=Qt.KeyboardModifier.ControlModifier,
        )
        assert qt_key_to_bytes(event) == b"\x03"

    def test_ctrl_d(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(
            Qt.Key.Key_D,
            modifiers=Qt.KeyboardModifier.ControlModifier,
        )
        assert qt_key_to_bytes(event) == b"\x04"

    def test_ctrl_z(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(
            Qt.Key.Key_Z,
            modifiers=Qt.KeyboardModifier.ControlModifier,
        )
        assert qt_key_to_bytes(event) == b"\x1a"

    def test_regular_text(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_A, text="a")
        assert qt_key_to_bytes(event) == b"a"

    def test_home_key(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_Home)
        assert qt_key_to_bytes(event) == b"\x1b[H"

    def test_end_key(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_End)
        assert qt_key_to_bytes(event) == b"\x1b[F"

    def test_delete_key(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_Delete)
        assert qt_key_to_bytes(event) == b"\x1b[3~"

    def test_f1_key(self):
        from PyQt6.QtCore import Qt

        event = self._make_key_event(Qt.Key.Key_F1)
        assert qt_key_to_bytes(event) == b"\x1bOP"


# ---------------------------------------------------------------------------
# pyte screen wrapper
# ---------------------------------------------------------------------------

class TestTerminalScreen:
    """Test pyte screen feed/resize logic."""

    def test_basic_feed(self):
        import pyte

        screen = pyte.Screen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Hello, World!")
        # Check that text appears on screen buffer
        line = screen.buffer[0]
        text = "".join(line[i].data for i in range(13))
        assert text == "Hello, World!"

    def test_newline_feed(self):
        import pyte

        screen = pyte.Screen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("Line1\r\nLine2")
        line0 = "".join(screen.buffer[0][i].data for i in range(5))
        line1 = "".join(screen.buffer[1][i].data for i in range(5))
        assert line0 == "Line1"
        assert line1 == "Line2"

    def test_resize(self):
        import pyte

        screen = pyte.Screen(80, 24)
        screen.resize(40, 100)
        assert screen.lines == 40
        assert screen.columns == 100

    def test_ansi_color_produces_fg(self):
        import pyte

        screen = pyte.Screen(80, 24)
        stream = pyte.Stream(screen)
        # Red text
        stream.feed("\x1b[31mRed\x1b[0m")
        char = screen.buffer[0][0]
        assert char.data == "R"
        assert char.fg == "red"

    def test_cursor_position_after_feed(self):
        import pyte

        screen = pyte.Screen(80, 24)
        stream = pyte.Stream(screen)
        stream.feed("ABC")
        assert screen.cursor.x == 3
        assert screen.cursor.y == 0

    def test_history_screen(self):
        import pyte

        screen = pyte.HistoryScreen(80, 5, history=100)
        stream = pyte.Stream(screen)
        # Write more lines than screen height to push into history
        for i in range(10):
            stream.feed(f"Line {i}\r\n")
        # History should have some lines
        assert len(screen.history.top) > 0
