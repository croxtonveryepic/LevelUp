"""Tests for the terminal emulator pure-logic components."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from levelup.gui.terminal_emulator import CatppuccinMochaColors, qt_key_to_bytes


def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


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


# ---------------------------------------------------------------------------
# TerminalEmulatorWidget
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestTerminalEmulatorWidget:
    """Tests for the TerminalEmulatorWidget with a mocked PtyBackend."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication

        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a TerminalEmulatorWidget with PtyBackend mocked out."""
        with patch("levelup.gui.terminal_emulator.PtyBackend") as MockPty:
            mock_pty = MagicMock()
            MockPty.return_value = mock_pty
            from levelup.gui.terminal_emulator import TerminalEmulatorWidget

            widget = TerminalEmulatorWidget()
        # The widget._pty is now the mock
        return widget

    # 1a: Construction & defaults
    def test_initial_state(self):
        widget = self._make_widget()
        assert widget.is_shell_running is False
        assert widget._cols == 80
        assert widget._rows == 24

    def test_screen_is_history_screen(self):
        import pyte

        widget = self._make_widget()
        assert isinstance(widget._screen, pyte.HistoryScreen)
        assert widget._screen.columns == 80
        assert widget._screen.lines == 24

    def test_focus_policy_is_strong_focus(self):
        from PyQt6.QtCore import Qt

        widget = self._make_widget()
        assert widget.focusPolicy() == Qt.FocusPolicy.StrongFocus

    # 1b: _on_pty_data feeds pyte screen
    def test_on_pty_data_feeds_text(self):
        widget = self._make_widget()
        widget._on_pty_data(b"Hello World")
        line = widget._screen.buffer[0]
        text = "".join(line[i].data for i in range(11))
        assert text == "Hello World"

    def test_on_pty_data_ansi_color(self):
        widget = self._make_widget()
        widget._on_pty_data(b"\x1b[31mRed\x1b[0m")
        char = widget._screen.buffer[0][0]
        assert char.data == "R"
        assert char.fg == "red"

    # 1c: _on_pty_exited
    def test_on_pty_exited_updates_state_and_emits_signal(self):
        widget = self._make_widget()
        widget._shell_running = True

        received: list[int] = []
        widget.shell_exited.connect(lambda code: received.append(code))

        widget._on_pty_exited(0)

        assert widget.is_shell_running is False
        assert received == [0]

    def test_on_pty_exited_nonzero_code(self):
        widget = self._make_widget()
        widget._shell_running = True

        received: list[int] = []
        widget.shell_exited.connect(lambda code: received.append(code))

        widget._on_pty_exited(42)
        assert received == [42]

    # 1d: send_command writes to PTY
    def test_send_command_writes_to_pty(self):
        widget = self._make_widget()
        widget._shell_running = True

        widget.send_command("echo hello")
        widget._pty.write.assert_called_once_with(b"echo hello\r")

    # 1e: send_interrupt writes Ctrl+C
    def test_send_interrupt_writes_ctrl_c(self):
        widget = self._make_widget()
        widget._shell_running = True

        widget.send_interrupt()
        widget._pty.write.assert_called_once_with(b"\x03")

    # 1f: no-ops when shell not running
    def test_send_command_noop_when_shell_not_running(self):
        widget = self._make_widget()
        assert widget._shell_running is False

        widget.send_command("test")
        widget._pty.write.assert_not_called()

    def test_send_interrupt_noop_when_shell_not_running(self):
        widget = self._make_widget()
        assert widget._shell_running is False

        widget.send_interrupt()
        widget._pty.write.assert_not_called()

    # 1g: _cell_in_selection (static method)
    def test_cell_in_single_row_selection(self):
        from levelup.gui.terminal_emulator import TerminalEmulatorWidget

        in_sel = TerminalEmulatorWidget._cell_in_selection
        # Selection from col 0 to col 5 on row 0
        assert in_sel(0, 0, (0, 0), (5, 0)) is True
        assert in_sel(3, 0, (0, 0), (5, 0)) is True
        assert in_sel(5, 0, (0, 0), (5, 0)) is True
        assert in_sel(6, 0, (0, 0), (5, 0)) is False
        # Wrong row
        assert in_sel(3, 1, (0, 0), (5, 0)) is False

    def test_cell_in_multi_row_selection(self):
        from levelup.gui.terminal_emulator import TerminalEmulatorWidget

        in_sel = TerminalEmulatorWidget._cell_in_selection
        # Selection from (3, 1) to (2, 3)
        # Row 1: col >= 3
        assert in_sel(3, 1, (3, 1), (2, 3)) is True
        assert in_sel(50, 1, (3, 1), (2, 3)) is True
        assert in_sel(2, 1, (3, 1), (2, 3)) is False
        # Row 2: all columns (middle row)
        assert in_sel(0, 2, (3, 1), (2, 3)) is True
        assert in_sel(79, 2, (3, 1), (2, 3)) is True
        # Row 3: col <= 2
        assert in_sel(0, 3, (3, 1), (2, 3)) is True
        assert in_sel(2, 3, (3, 1), (2, 3)) is True
        assert in_sel(3, 3, (3, 1), (2, 3)) is False
        # Outside selection rows
        assert in_sel(3, 0, (3, 1), (2, 3)) is False
        assert in_sel(0, 4, (3, 1), (2, 3)) is False

    def test_cell_in_single_cell_selection(self):
        from levelup.gui.terminal_emulator import TerminalEmulatorWidget

        in_sel = TerminalEmulatorWidget._cell_in_selection
        assert in_sel(5, 5, (5, 5), (5, 5)) is True
        assert in_sel(4, 5, (5, 5), (5, 5)) is False
        assert in_sel(6, 5, (5, 5), (5, 5)) is False

    # 1h: _normalized_selection ordering
    def test_normalized_selection_reversed(self):
        widget = self._make_widget()
        widget._selection_start = (5, 2)
        widget._selection_end = (1, 0)

        start, end = widget._normalized_selection()
        assert start == (1, 0)
        assert end == (5, 2)

    def test_normalized_selection_already_ordered(self):
        widget = self._make_widget()
        widget._selection_start = (1, 0)
        widget._selection_end = (5, 2)

        start, end = widget._normalized_selection()
        assert start == (1, 0)
        assert end == (5, 2)

    def test_normalized_selection_same_point(self):
        widget = self._make_widget()
        widget._selection_start = (3, 3)
        widget._selection_end = (3, 3)

        start, end = widget._normalized_selection()
        assert start == (3, 3)
        assert end == (3, 3)

    def test_normalized_selection_none(self):
        widget = self._make_widget()
        start, end = widget._normalized_selection()
        assert start is None
        assert end is None

    # 1i: _get_selected_text
    def test_get_selected_text(self):
        widget = self._make_widget()
        widget._on_pty_data(b"Hello World\r\nSecond Line")

        # Select "World" on first line (cols 6-10, row 0)
        widget._selection_start = (6, 0)
        widget._selection_end = (10, 0)

        text = widget._get_selected_text()
        assert text == "World"

    def test_get_selected_text_multiline(self):
        widget = self._make_widget()
        widget._on_pty_data(b"AAABBB\r\nCCCDDD")

        # Select from col 3 row 0 to col 2 row 1 -> "BBB\nCCC"
        widget._selection_start = (3, 0)
        widget._selection_end = (2, 1)

        text = widget._get_selected_text()
        assert text == "BBB\nCCC"

    def test_get_selected_text_empty_when_no_selection(self):
        widget = self._make_widget()
        assert widget._get_selected_text() == ""

    # 1j: _recalculate_grid
    def test_recalculate_grid_updates_dimensions(self):
        widget = self._make_widget()
        cw = widget._cell_width
        ch = widget._cell_height

        # Resize to a size that gives different cols/rows than the 80x24 default.
        # Use a generous pixel size and verify the result is in the expected range
        # (int truncation of float division can lose 1 cell).
        target_cols = 40
        target_rows = 10
        widget.resize(int(cw * target_cols) + 1, int(ch * target_rows) + 1)
        widget._recalculate_grid()

        assert widget._cols != 80  # Changed from default
        assert widget._rows != 24
        assert abs(widget._cols - target_cols) <= 1
        assert abs(widget._rows - target_rows) <= 1

    def test_recalculate_grid_minimum_dimensions(self):
        widget = self._make_widget()
        # Resize to very small — should clamp to 10 cols, 2 rows minimum
        widget.resize(1, 1)
        widget._recalculate_grid()

        assert widget._cols >= 10
        assert widget._rows >= 2

    def test_recalculate_grid_noop_for_zero_size(self):
        widget = self._make_widget()
        original_cols = widget._cols
        original_rows = widget._rows

        widget.resize(0, 0)
        widget._recalculate_grid()

        # Should not change when size is zero
        assert widget._cols == original_cols
        assert widget._rows == original_rows

    # 1k: close_shell
    def test_close_shell_cleans_up(self):
        widget = self._make_widget()
        widget._shell_running = True

        widget.close_shell()

        assert widget.is_shell_running is False
        widget._pty.close.assert_called_once()
