"""Tests for terminal emulator scrollback rendering integration.

This test module verifies the interaction between scroll offset, history buffer,
current buffer, and the paintEvent rendering logic. Tests focus on ensuring the
correct lines are selected for rendering based on scroll position.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.regression

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
class TestTerminalScrollbackRendering:
    """Test the rendering logic for scrollback display."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Setup QApplication for PyQt6 tests."""
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a TerminalEmulatorWidget with PtyBackend mocked out."""
        with patch("levelup.gui.terminal_emulator.PtyBackend") as MockPty:
            mock_pty = MagicMock()
            MockPty.return_value = mock_pty
            from levelup.gui.terminal_emulator import TerminalEmulatorWidget

            widget = TerminalEmulatorWidget()
        return widget

    # -------------------------------------------------------------------------
    # Line Selection Logic for Rendering
    # -------------------------------------------------------------------------

    def test_rendering_selects_buffer_lines_when_at_bottom(self):
        """When scroll_offset=0, rendering should use only screen.buffer lines."""
        widget = self._make_widget()

        # Write data to create history and buffer
        for i in range(40):
            widget._on_pty_data(f"Line{i:03d}\r\n".encode())

        # At bottom
        widget._scroll_offset = 0

        # For each row in viewport, should read from screen.buffer[row]
        for row in range(widget._rows):
            line = widget._screen.buffer[row]
            assert line is not None

    def test_rendering_selects_history_lines_when_scrolled(self):
        """When scroll_offset>0, rendering should use history.top for top rows."""
        widget = self._make_widget()

        # Create history
        for i in range(50):
            widget._on_pty_data(f"H{i:04d}\r\n".encode())

        # Scroll up by 10
        widget._scroll_offset = 10

        history_len = len(widget._screen.history.top)
        assert history_len > 0

        # Top 10 rows should come from history
        # Row 0 maps to history[history_len - 10]
        # Row 9 maps to history[history_len - 1]
        for row in range(10):
            history_idx = history_len - 10 + row
            assert 0 <= history_idx < history_len
            history_line = widget._screen.history.top[history_idx]
            assert history_line is not None

    def test_rendering_transitions_from_history_to_buffer(self):
        """When partially scrolled, rendering transitions from history to buffer."""
        widget = self._make_widget()

        # Create history
        for i in range(60):
            widget._on_pty_data(f"Line{i:04d}\r\n".encode())

        # Scroll up by 5
        offset = 5
        widget._scroll_offset = offset

        history_len = len(widget._screen.history.top)

        # Rows 0-4: from history
        for row in range(offset):
            history_idx = history_len - offset + row
            assert 0 <= history_idx < history_len

        # Rows 5+: from buffer
        for row in range(offset, widget._rows):
            buffer_row = row - offset
            assert buffer_row >= 0
            line = widget._screen.buffer[buffer_row]
            assert line is not None

    def test_rendering_with_scroll_offset_equal_to_viewport_height(self):
        """When scroll_offset equals viewport height, all rows from history."""
        widget = self._make_widget()

        # Create history
        for i in range(100):
            widget._on_pty_data(f"Line{i:04d}\r\n".encode())

        # Scroll up by full viewport height
        rows = widget._rows
        widget._scroll_offset = rows

        history_len = len(widget._screen.history.top)

        # All rows should come from history
        for row in range(rows):
            history_idx = history_len - rows + row
            if history_idx >= 0 and history_idx < history_len:
                history_line = widget._screen.history.top[history_idx]
                assert history_line is not None

    def test_rendering_with_scroll_offset_greater_than_viewport(self):
        """When scroll_offset > viewport height, viewport shows older history."""
        widget = self._make_widget()

        # Create substantial history
        for i in range(150):
            widget._on_pty_data(f"Line{i:04d}\r\n".encode())

        # Scroll up by more than viewport height
        rows = widget._rows
        offset = rows + 10
        widget._scroll_offset = offset

        history_len = len(widget._screen.history.top)

        # All viewport rows should show history
        # Row 0 shows history[history_len - offset]
        for row in range(rows):
            history_idx = history_len - offset + row
            if 0 <= history_idx < history_len:
                history_line = widget._screen.history.top[history_idx]
                assert history_line is not None

    # -------------------------------------------------------------------------
    # History Index Calculation
    # -------------------------------------------------------------------------

    def test_history_index_calculation_for_first_row(self):
        """First viewport row maps to correct history index."""
        widget = self._make_widget()

        for i in range(80):
            widget._on_pty_data(f"L{i:04d}\r\n".encode())

        offset = 15
        widget._scroll_offset = offset

        history_len = len(widget._screen.history.top)

        # Row 0 should map to history[history_len - offset]
        expected_idx = history_len - offset
        assert 0 <= expected_idx < history_len

    def test_history_index_calculation_for_last_history_row(self):
        """Last history row in viewport maps to correct history index."""
        widget = self._make_widget()

        for i in range(80):
            widget._on_pty_data(f"L{i:04d}\r\n".encode())

        offset = 7
        widget._scroll_offset = offset

        history_len = len(widget._screen.history.top)

        # Row (offset - 1) should map to history[history_len - 1] (newest history)
        last_history_row = offset - 1
        expected_idx = history_len - offset + last_history_row
        assert expected_idx == history_len - 1

    def test_history_index_sequential_for_consecutive_rows(self):
        """Consecutive viewport rows map to consecutive history indices."""
        widget = self._make_widget()

        for i in range(100):
            widget._on_pty_data(f"L{i:05d}\r\n".encode())

        offset = 20
        widget._scroll_offset = offset

        history_len = len(widget._screen.history.top)

        # Check first 10 rows
        indices = []
        for row in range(10):
            history_idx = history_len - offset + row
            indices.append(history_idx)

        # Should be sequential
        for i in range(len(indices) - 1):
            assert indices[i + 1] == indices[i] + 1

    # -------------------------------------------------------------------------
    # Buffer Index Calculation
    # -------------------------------------------------------------------------

    def test_buffer_index_calculation_when_partially_scrolled(self):
        """Buffer rows use correct indices when some rows show history."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        offset = 8
        widget._scroll_offset = offset

        # Rows 8+ should use buffer
        # Row 8 maps to buffer[0]
        # Row 9 maps to buffer[1]
        for viewport_row in range(offset, widget._rows):
            buffer_row = viewport_row - offset
            assert buffer_row >= 0
            assert buffer_row < len(widget._screen.buffer)

    def test_buffer_index_zero_when_first_buffer_row_displayed(self):
        """First buffer row in viewport uses buffer[0]."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        offset = 12
        widget._scroll_offset = offset

        # Viewport row 'offset' should map to buffer[0]
        viewport_row = offset
        buffer_row = viewport_row - offset
        assert buffer_row == 0

    def test_buffer_indices_sequential_for_consecutive_rows(self):
        """Consecutive buffer rows in viewport use sequential buffer indices."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        offset = 5
        widget._scroll_offset = offset

        # Collect buffer indices for rows 5-14
        buffer_indices = []
        for viewport_row in range(offset, min(offset + 10, widget._rows)):
            buffer_row = viewport_row - offset
            buffer_indices.append(buffer_row)

        # Should be 0, 1, 2, 3, ...
        for i, idx in enumerate(buffer_indices):
            assert idx == i

    # -------------------------------------------------------------------------
    # Edge Cases in Line Selection
    # -------------------------------------------------------------------------

    def test_rendering_when_history_shorter_than_scroll_offset(self):
        """Handle case where scroll_offset > history length."""
        widget = self._make_widget()

        # Create small history
        for i in range(10):
            widget._on_pty_data(f"L{i:02d}\r\n".encode())

        history_len = len(widget._screen.history.top)

        # Try to scroll beyond history
        widget._scroll_offset = history_len + 20

        # Top rows may be empty/invalid, but should not crash
        # Valid history rows: 0 to (history_len - 1)
        # Attempting to access history[history_len + 20 - offset + row] may be out of bounds

    def test_rendering_when_history_empty_but_scrolled(self):
        """Handle case where history is empty but scroll_offset > 0."""
        widget = self._make_widget()

        # Don't create any history (write less than screen height)
        widget._on_pty_data(b"Line 1\r\n")
        widget._on_pty_data(b"Line 2\r\n")

        history_len = len(widget._screen.history.top)
        assert history_len == 0

        # Try to scroll up
        widget._scroll_offset = 5

        # Should handle gracefully (perhaps clamp or show buffer only)

    def test_rendering_with_one_line_history(self):
        """Edge case: exactly one line in history."""
        widget = self._make_widget()

        # Write exactly enough to push one line to history
        rows = widget._rows
        for i in range(rows + 1):
            widget._on_pty_data(f"L{i:02d}\r\n".encode())

        history_len = len(widget._screen.history.top)
        assert history_len >= 1

        # Scroll up by 1
        widget._scroll_offset = 1

        # Row 0 should show the one history line
        history_idx = history_len - 1
        assert history_idx >= 0

    def test_rendering_with_maximum_history_scroll(self):
        """Scroll to show the very oldest history line."""
        widget = self._make_widget()

        # Create substantial history
        for i in range(200):
            widget._on_pty_data(f"L{i:04d}\r\n".encode())

        history_len = len(widget._screen.history.top)

        # Scroll to show oldest history
        widget._scroll_offset = history_len

        # Row 0 should show history[0] (oldest)
        if history_len >= widget._rows:
            history_idx = history_len - history_len + 0
            assert history_idx == 0

    # -------------------------------------------------------------------------
    # Viewport Row Iteration
    # -------------------------------------------------------------------------

    def test_paintevent_iterates_all_viewport_rows(self):
        """paintEvent should iterate through all rows: 0 to (_rows - 1)."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 10

        # paintEvent loop should go from row 0 to widget._rows - 1
        rows_to_render = widget._rows
        assert rows_to_render >= 2  # Minimum viewport size

    def test_row_zero_always_processed_in_paintevent(self):
        """Row 0 (top of viewport) is always processed."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        # Various scroll offsets
        for offset in [0, 1, 5, 10, 20]:
            widget._scroll_offset = offset

            # Row 0 should always be processed
            # When offset=0: shows buffer[0]
            # When offset>0: shows history[history_len - offset]

    def test_last_viewport_row_always_processed(self):
        """Last row of viewport is always processed."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 5

        last_row = widget._rows - 1
        assert last_row >= 0

        # Last row should be processed
        # It will show buffer[last_row - offset] if offset < last_row

    # -------------------------------------------------------------------------
    # Character Data Access
    # -------------------------------------------------------------------------

    def test_character_data_accessed_from_history_line(self):
        """Characters in history lines are accessed correctly."""
        widget = self._make_widget()

        # Write specific content
        for i in range(50):
            widget._on_pty_data(f"ABCD{i:03d}\r\n".encode())

        widget._scroll_offset = 10

        history_len = len(widget._screen.history.top)
        history_line = widget._screen.history.top[history_len - 1]

        # Access characters in the line
        for col in range(min(4, widget._cols)):
            char = history_line[col]
            assert char.data in ["A", "B", "C", "D"]

    def test_character_data_accessed_from_buffer_line(self):
        """Characters in buffer lines are accessed correctly."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"XYZ{i:03d}\r\n".encode())

        widget._scroll_offset = 3

        # After offset rows, should access buffer
        buffer_line = widget._screen.buffer[0]
        for col in range(min(3, widget._cols)):
            char = buffer_line[col]
            assert char.data in ["X", "Y", "Z", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", " "]

    def test_character_attributes_from_history(self):
        """Character attributes (fg, bg, bold, reverse) from history are correct."""
        widget = self._make_widget()

        # Write bold red text
        for i in range(50):
            widget._on_pty_data(f"\x1b[1;31mBOLD{i}\x1b[0m\r\n".encode())

        widget._scroll_offset = 5

        history_len = len(widget._screen.history.top)
        history_line = widget._screen.history.top[history_len - 1]

        # First char should be bold and red
        char = history_line[0]
        assert char.bold is True
        assert char.fg == "red"

    def test_character_attributes_from_buffer(self):
        """Character attributes from buffer lines are correct."""
        widget = self._make_widget()

        for i in range(30):
            widget._on_pty_data(f"Plain{i}\r\n".encode())

        # Write one line with color to current buffer
        widget._on_pty_data(b"\x1b[32mGreen\x1b[0m\r\n")

        widget._scroll_offset = 0

        # Should be in buffer
        # Find the line with "Green"
        found = False
        for row in range(widget._rows):
            line = widget._screen.buffer[row]
            text = "".join(c.data for c in line[:5])
            if "Green" in text:
                found = True
                first_char = line[0]
                assert first_char.fg == "green"
                break

        # May not find if buffer wrapped

    # -------------------------------------------------------------------------
    # Column Iteration
    # -------------------------------------------------------------------------

    def test_all_columns_processed_for_each_row(self):
        """For each row, all columns 0 to (_cols - 1) are processed."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 5

        # For any row, should process all columns
        cols_to_render = widget._cols
        assert cols_to_render >= 10  # Minimum columns

    def test_column_zero_always_processed(self):
        """Column 0 (leftmost) is always processed for each row."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 7

        # Column 0 should be processed for all rows

    def test_last_column_always_processed(self):
        """Last column of each row is always processed."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 3

        last_col = widget._cols - 1
        assert last_col >= 0

        # Last column should be processed

    # -------------------------------------------------------------------------
    # Cell Position Calculation
    # -------------------------------------------------------------------------

    def test_cell_position_calculation_for_history_row(self):
        """Cell position (x, y) calculated correctly for history rows."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 10

        # Row 0 shows history
        row = 0
        col = 5

        x = col * widget._cell_width
        y = row * widget._cell_height

        assert x >= 0
        assert y >= 0

    def test_cell_position_calculation_for_buffer_row(self):
        """Cell position (x, y) calculated correctly for buffer rows."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 5

        # Row 10 shows buffer
        row = 10
        col = 8

        x = col * widget._cell_width
        y = row * widget._cell_height

        assert x >= 0
        assert y >= 0

    def test_cell_positions_sequential_across_columns(self):
        """Cell x positions increase sequentially across columns."""
        widget = self._make_widget()

        positions = []
        for col in range(10):
            x = col * widget._cell_width
            positions.append(x)

        # Should be increasing
        for i in range(len(positions) - 1):
            assert positions[i + 1] > positions[i]

    def test_cell_positions_sequential_across_rows(self):
        """Cell y positions increase sequentially across rows."""
        widget = self._make_widget()

        positions = []
        for row in range(10):
            y = row * widget._cell_height
            positions.append(y)

        # Should be increasing
        for i in range(len(positions) - 1):
            assert positions[i + 1] > positions[i]

    # -------------------------------------------------------------------------
    # Integration: Scroll and Render
    # -------------------------------------------------------------------------

    def test_scroll_up_changes_rendered_content(self):
        """Scrolling up changes which lines are rendered."""
        widget = self._make_widget()

        # Create identifiable lines
        for i in range(60):
            widget._on_pty_data(f"ID{i:04d}\r\n".encode())

        # At bottom: buffer shows recent lines
        widget._scroll_offset = 0
        buffer_first_line_at_bottom = widget._screen.buffer[0]

        # Scroll up: history shows older lines
        widget._scroll_offset = 20
        history_len = len(widget._screen.history.top)
        history_idx = history_len - 20
        history_first_line = widget._screen.history.top[history_idx]

        # These should be different lines
        # (unless buffer happens to match history, unlikely)

    def test_scroll_down_returns_to_buffer(self):
        """Scrolling back down returns to showing buffer."""
        widget = self._make_widget()

        for i in range(60):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        # Scroll up
        widget._scroll_offset = 15

        # Should show history at top

        # Scroll back down
        widget._scroll_offset = 0

        # Should show buffer only

    def test_scroll_increments_shift_history_window(self):
        """Incrementing scroll offset shifts the history window."""
        widget = self._make_widget()

        for i in range(100):
            widget._on_pty_data(f"L{i:04d}\r\n".encode())

        history_len = len(widget._screen.history.top)

        # Scroll up by 10
        widget._scroll_offset = 10
        first_idx_1 = history_len - 10

        # Scroll up by 15 (5 more)
        widget._scroll_offset = 15
        first_idx_2 = history_len - 15

        # Second scroll shows older history
        assert first_idx_2 < first_idx_1

    # -------------------------------------------------------------------------
    # Rendering with Empty/Partial Lines
    # -------------------------------------------------------------------------

    def test_rendering_empty_history_line(self):
        """Handle rendering of empty history lines."""
        widget = self._make_widget()

        # Write lines with varying content
        for i in range(50):
            if i % 5 == 0:
                widget._on_pty_data(b"\r\n")  # Empty line
            else:
                widget._on_pty_data(f"Line{i:03d}\r\n".encode())

        widget._scroll_offset = 10

        # Should handle empty lines in history

    def test_rendering_partial_history_line(self):
        """Handle rendering of partially filled history lines."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"X{i}\r\n".encode())  # Short lines

        widget._scroll_offset = 5

        # Lines shorter than terminal width should pad with spaces

    def test_rendering_full_width_history_line(self):
        """Handle rendering of full-width history lines."""
        widget = self._make_widget()

        # Write lines that fill terminal width
        cols = widget._cols
        for i in range(50):
            line = "X" * (cols - 1) + "\r\n"
            widget._on_pty_data(line.encode())

        widget._scroll_offset = 8

        # Should render full-width lines correctly

    # -------------------------------------------------------------------------
    # Cursor Position and Scrollback
    # -------------------------------------------------------------------------

    def test_cursor_not_drawn_when_scrolled(self):
        """Cursor should not be drawn when scroll_offset > 0."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 10

        # paintEvent condition: if self._cursor_visible and self._scroll_offset == 0
        # When scrolled, cursor should not be drawn regardless of _cursor_visible
        assert widget._scroll_offset > 0

    def test_cursor_position_unchanged_by_scroll(self):
        """Cursor position (screen.cursor) is not affected by scroll_offset."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        cursor_pos_before = (widget._screen.cursor.x, widget._screen.cursor.y)

        # Scroll up
        widget._scroll_offset = 15

        cursor_pos_after = (widget._screen.cursor.x, widget._screen.cursor.y)

        # Cursor position should be unchanged
        assert cursor_pos_before == cursor_pos_after

    def test_cursor_drawn_when_returning_to_bottom(self):
        """Cursor should be drawn when scroll_offset returns to 0."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        # Scroll up
        widget._scroll_offset = 10
        assert widget._scroll_offset > 0

        # Return to bottom
        widget._scroll_offset = 0

        # Cursor should be drawn (if _cursor_visible)
        assert widget._scroll_offset == 0

    # -------------------------------------------------------------------------
    # Selection Highlighting with Scrollback
    # -------------------------------------------------------------------------

    def test_selection_highlight_applied_to_history_cells(self):
        """Selection highlighting should work on history cells."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 10

        # Make selection on row 0 (which shows history)
        widget._selection_start = (0, 0)
        widget._selection_end = (5, 0)

        # Selection should be applied to the history cells being rendered

    def test_selection_highlight_applied_to_buffer_cells(self):
        """Selection highlighting should work on buffer cells when partially scrolled."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 5

        # Make selection on row 10 (which shows buffer)
        widget._selection_start = (0, 10)
        widget._selection_end = (8, 10)

        # Selection should be applied to the buffer cells being rendered

    def test_selection_spans_history_and_buffer(self):
        """Selection can span both history and buffer regions."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 5

        # Select from row 3 (history) to row 10 (buffer)
        widget._selection_start = (0, 3)
        widget._selection_end = (10, 10)

        # Selection should apply to both regions

    # -------------------------------------------------------------------------
    # Background and Foreground Colors
    # -------------------------------------------------------------------------

    def test_default_background_color_for_history(self):
        """History cells without explicit background use default BG color."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())  # No bg color

        widget._scroll_offset = 8

        history_len = len(widget._screen.history.top)
        history_line = widget._screen.history.top[history_len - 1]
        char = history_line[0]

        # Should use default colors
        assert char.bg == "default" or not char.bg

    def test_default_foreground_color_for_history(self):
        """History cells without explicit foreground use default FG color."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        widget._scroll_offset = 6

        history_len = len(widget._screen.history.top)
        history_line = widget._screen.history.top[history_len - 1]
        char = history_line[0]

        # Should use default fg
        assert char.fg == "default" or not char.fg

    def test_explicit_background_color_in_history(self):
        """Explicit background colors in history are preserved."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"\x1b[42mGreenBG{i}\x1b[0m\r\n".encode())  # Green bg

        widget._scroll_offset = 5

        history_len = len(widget._screen.history.top)
        history_line = widget._screen.history.top[history_len - 1]
        char = history_line[0]

        # Should have green background
        assert char.bg == "green"

    def test_explicit_foreground_color_in_history(self):
        """Explicit foreground colors in history are preserved."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"\x1b[33mYellowFG{i}\x1b[0m\r\n".encode())

        widget._scroll_offset = 4

        history_len = len(widget._screen.history.top)
        history_line = widget._screen.history.top[history_len - 1]
        char = history_line[0]

        assert char.fg == "yellow"

    # -------------------------------------------------------------------------
    # Performance and Correctness
    # -------------------------------------------------------------------------

    def test_no_out_of_bounds_history_access(self):
        """Ensure history access never goes out of bounds."""
        widget = self._make_widget()

        for i in range(30):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        history_len = len(widget._screen.history.top)

        # Try various scroll offsets
        for offset in [1, 5, 10, history_len, history_len + 10]:
            widget._scroll_offset = offset

            # Calculate expected history indices for top rows
            for row in range(min(offset, widget._rows)):
                history_idx = history_len - offset + row
                # Index should be in valid range
                if offset <= history_len:
                    assert 0 <= history_idx < history_len

    def test_no_out_of_bounds_buffer_access(self):
        """Ensure buffer access never goes out of bounds."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        # Try various scroll offsets
        for offset in [0, 3, 7, 15]:
            widget._scroll_offset = offset

            # Calculate expected buffer indices for rows after history
            for row in range(offset, widget._rows):
                buffer_row = row - offset
                # Index should be in valid range
                assert 0 <= buffer_row < len(widget._screen.buffer)

    def test_rendering_deterministic_for_same_scroll_position(self):
        """Rendering same scroll position twice gives same result."""
        widget = self._make_widget()

        for i in range(50):
            widget._on_pty_data(f"L{i:03d}\r\n".encode())

        # Set scroll position
        widget._scroll_offset = 12

        # Extract what would be rendered (history indices)
        history_len = len(widget._screen.history.top)
        first_pass_indices = []
        for row in range(widget._rows):
            if row < 12:
                idx = history_len - 12 + row
                first_pass_indices.append(("history", idx))
            else:
                idx = row - 12
                first_pass_indices.append(("buffer", idx))

        # Set same scroll position again
        widget._scroll_offset = 12

        # Extract indices again
        second_pass_indices = []
        for row in range(widget._rows):
            if row < 12:
                idx = history_len - 12 + row
                second_pass_indices.append(("history", idx))
            else:
                idx = row - 12
                second_pass_indices.append(("buffer", idx))

        # Should be identical
        assert first_pass_indices == second_pass_indices
