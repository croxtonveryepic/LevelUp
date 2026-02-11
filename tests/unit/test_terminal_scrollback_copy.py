"""Tests for terminal text copying with scrollback support.

This test module verifies that _get_selected_text() correctly extracts text
from the composite view (history + buffer) when scrolled up, matching the
same logic used by paintEvent() for rendering.

These tests are written in TDD style and will initially FAIL until the
_get_selected_text() method is updated to account for scroll offset.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


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
class TestTerminalScrollbackCopy:
    """Test that _get_selected_text() correctly extracts text when scrolled up."""

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

    def _fill_history(self, widget, num_lines: int):
        """Helper to fill terminal with enough lines to push some into history."""
        # Write more lines than the screen height to push into history
        for i in range(num_lines):
            widget._on_pty_data(f"Line {i}\r\n".encode())

    # -------------------------------------------------------------------------
    # Core Requirement: Copy from composite view when scrolled up
    # -------------------------------------------------------------------------

    def test_copy_from_buffer_when_at_bottom(self):
        """AC: When _scroll_offset == 0, text copying reads from current buffer (existing behavior)."""
        widget = self._make_widget()

        # Write identifiable text to buffer
        widget._on_pty_data(b"Current line 1\r\n")
        widget._on_pty_data(b"Current line 2\r\n")
        widget._on_pty_data(b"Current line 3\r\n")

        # At bottom (no scroll)
        widget._scroll_offset = 0

        # Select text from first visible row
        widget._selection_start = (0, 0)
        widget._selection_end = (13, 0)

        # Should copy from buffer
        text = widget._get_selected_text()
        assert text == "Current line 1"

    def test_copy_from_history_when_scrolled_up(self):
        """AC: When _scroll_offset > 0, text copying reads from visible history lines."""
        widget = self._make_widget()

        # Create identifiable history lines
        for i in range(30):
            widget._on_pty_data(f"History {i:02d}\r\n".encode())

        # Write current buffer lines (these will be at the bottom)
        widget._on_pty_data(b"Current 0\r\n")
        widget._on_pty_data(b"Current 1\r\n")

        # Scroll up by 5 lines
        widget._scroll_offset = 5

        # Select text from row 0 (which should now show history, not current buffer)
        widget._selection_start = (0, 0)
        widget._selection_end = (9, 0)

        # Should copy from history, not from current buffer
        text = widget._get_selected_text()

        # Calculate which history line should be at row 0
        history_len = len(widget._screen.history.top)
        history_idx = history_len - 5 + 0  # row = 0, offset = 5
        expected_line = widget._screen.history.top[history_idx]
        expected_text = "".join(expected_line[col].data if expected_line[col].data else " " for col in range(10)).rstrip()

        assert text == expected_text

    def test_copy_multiline_selection_spanning_history_and_buffer(self):
        """AC: Multi-line selection spanning both history and buffer regions copies correct composite text."""
        widget = self._make_widget()

        # Create history
        for i in range(40):
            widget._on_pty_data(f"Hist{i:03d}\r\n".encode())

        # Write current buffer
        for i in range(5):
            widget._on_pty_data(f"Buff{i}\r\n".encode())

        # Scroll up by 3 lines
        # Top 3 rows show history, remaining rows show buffer
        widget._scroll_offset = 3

        # Select from row 1 (history) to row 4 (buffer)
        widget._selection_start = (0, 1)
        widget._selection_end = (5, 4)

        text = widget._get_selected_text()
        lines = text.split("\n")

        # Should have 4 lines (rows 1, 2, 3, 4)
        assert len(lines) == 4

        # First two lines (rows 1, 2) should be from history
        history_len = len(widget._screen.history.top)

        # Row 1: history_idx = history_len - 3 + 1
        row1_history_idx = history_len - 3 + 1
        expected_row1 = widget._screen.history.top[row1_history_idx]
        expected_row1_text = "".join(expected_row1[col].data if expected_row1[col].data else " " for col in range(widget._cols)).rstrip()

        # Row 2: history_idx = history_len - 3 + 2
        row2_history_idx = history_len - 3 + 2
        expected_row2 = widget._screen.history.top[row2_history_idx]
        expected_row2_text = "".join(expected_row2[col].data if expected_row2[col].data else " " for col in range(widget._cols)).rstrip()

        assert lines[0] == expected_row1_text
        assert lines[1] == expected_row2_text

        # Last two lines (rows 3, 4) should be from buffer
        # Row 3: buffer_row = 3 - 3 = 0
        buffer_row_3 = widget._screen.buffer[0]
        expected_row3_text = "".join(buffer_row_3[col].data if buffer_row_3[col].data else " " for col in range(widget._cols)).rstrip()

        # Row 4: buffer_row = 4 - 3 = 1
        buffer_row_4 = widget._screen.buffer[1]
        expected_row4_text = "".join(buffer_row_4[col].data if buffer_row_4[col].data else " " for col in range(6)).rstrip()

        assert lines[2] == expected_row3_text
        assert lines[3][:6].rstrip() == expected_row4_text[:6].rstrip()

    def test_copy_from_history_at_different_scroll_offsets(self):
        """AC: Copying correctly reads from history at various scroll offsets."""
        widget = self._make_widget()

        # Create identifiable history
        for i in range(50):
            widget._on_pty_data(f"H{i:04d}\r\n".encode())

        # Test at different scroll offsets
        for offset in [1, 5, 10, 15]:
            widget._scroll_offset = offset

            # Select first row
            widget._selection_start = (0, 0)
            widget._selection_end = (4, 0)

            text = widget._get_selected_text()

            # Calculate expected text from history
            history_len = len(widget._screen.history.top)
            history_idx = history_len - offset + 0
            expected_line = widget._screen.history.top[history_idx]
            expected_text = "".join(expected_line[col].data if expected_line[col].data else " " for col in range(5)).rstrip()

            assert text == expected_text, f"Failed at offset {offset}"

    def test_copy_from_buffer_rows_when_partially_scrolled(self):
        """AC: When scrolled up, rows >= scroll_offset correctly read from buffer."""
        widget = self._make_widget()

        # Create history
        for i in range(30):
            widget._on_pty_data(f"Old{i:02d}\r\n".encode())

        # Write identifiable buffer lines
        widget._on_pty_data(b"Buffer_0\r\n")
        widget._on_pty_data(b"Buffer_1\r\n")
        widget._on_pty_data(b"Buffer_2\r\n")

        # Scroll up by 2 lines
        # Rows 0-1 show history, rows 2+ show buffer
        widget._scroll_offset = 2

        # Select from row 3 (should be buffer[1])
        widget._selection_start = (0, 3)
        widget._selection_end = (7, 3)

        text = widget._get_selected_text()

        # Row 3, offset 2: buffer_row = 3 - 2 = 1
        expected_line = widget._screen.buffer[1]
        expected_text = "".join(expected_line[col].data if expected_line[col].data else " " for col in range(8)).rstrip()

        assert text == expected_text

    # -------------------------------------------------------------------------
    # Edge Cases
    # -------------------------------------------------------------------------

    def test_copy_with_empty_history_and_scroll_offset(self):
        """AC: Copying when history is empty but scroll offset > 0 handles gracefully."""
        widget = self._make_widget()

        # Write only a few lines (not enough to create history)
        widget._on_pty_data(b"Line 1\r\n")
        widget._on_pty_data(b"Line 2\r\n")

        # Verify no history
        assert len(widget._screen.history.top) == 0

        # Try to scroll up (artificially)
        widget._scroll_offset = 5

        # Attempt to select and copy
        widget._selection_start = (0, 0)
        widget._selection_end = (5, 0)

        # Should handle gracefully without crashing
        text = widget._get_selected_text()
        # May be empty or fallback to buffer - shouldn't crash
        assert isinstance(text, str)

    def test_copy_when_scroll_offset_exceeds_history_length(self):
        """AC: Copying when scrolled beyond available history length handles gracefully."""
        widget = self._make_widget()

        # Create small history
        for i in range(10):
            widget._on_pty_data(f"Short{i}\r\n".encode())

        history_len = len(widget._screen.history.top)

        # Set scroll offset beyond history length
        widget._scroll_offset = history_len + 10

        # Try to copy from row 0
        widget._selection_start = (0, 0)
        widget._selection_end = (4, 0)

        # Should handle gracefully
        text = widget._get_selected_text()
        assert isinstance(text, str)

    def test_copy_single_line_from_history(self):
        """AC: Single-line selection from history copies correctly."""
        widget = self._make_widget()

        # Create history with identifiable content
        for i in range(35):
            widget._on_pty_data(f"Line_{i:03d}_content\r\n".encode())

        # Scroll up by 8 lines
        widget._scroll_offset = 8

        # Select a portion of row 3 (which is in history)
        widget._selection_start = (0, 3)
        widget._selection_end = (16, 3)

        text = widget._get_selected_text()

        # Calculate expected text
        history_len = len(widget._screen.history.top)
        history_idx = history_len - 8 + 3
        expected_line = widget._screen.history.top[history_idx]
        expected_text = "".join(expected_line[col].data if expected_line[col].data else " " for col in range(17)).rstrip()

        assert text == expected_text

    def test_copy_partial_columns_from_history(self):
        """AC: Partial column selection from history line copies correct substring."""
        widget = self._make_widget()

        # Create history
        for i in range(40):
            widget._on_pty_data(f"ABCDEFGHIJ{i:02d}\r\n".encode())

        # Scroll up
        widget._scroll_offset = 5

        # Select columns 3-7 from row 2 (history)
        widget._selection_start = (3, 2)
        widget._selection_end = (7, 2)

        text = widget._get_selected_text()

        # Should be "DEFGH" from the history line
        history_len = len(widget._screen.history.top)
        history_idx = history_len - 5 + 2
        expected_line = widget._screen.history.top[history_idx]
        expected_text = "".join(expected_line[col].data if expected_line[col].data else " " for col in range(3, 8)).rstrip()

        assert text == expected_text

    def test_copy_entire_viewport_when_scrolled(self):
        """AC: Selecting entire viewport when scrolled copies correct composite text."""
        widget = self._make_widget()

        # Create history
        for i in range(60):
            widget._on_pty_data(f"HistLine{i:03d}\r\n".encode())

        # Write buffer
        for i in range(5):
            widget._on_pty_data(f"BuffLine{i}\r\n".encode())

        rows = widget._rows
        cols = widget._cols

        # Scroll up by 10 lines
        widget._scroll_offset = 10

        # Select entire viewport (all rows, all columns)
        widget._selection_start = (0, 0)
        widget._selection_end = (cols - 1, rows - 1)

        text = widget._get_selected_text()
        lines = text.split("\n")

        # Should have 'rows' number of lines
        assert len(lines) == rows

        # Top 10 lines should be from history
        history_len = len(widget._screen.history.top)
        for row in range(10):
            history_idx = history_len - 10 + row
            expected_line = widget._screen.history.top[history_idx]
            expected_text = "".join(expected_line[col].data if expected_line[col].data else " " for col in range(cols)).rstrip()
            assert lines[row] == expected_text

        # Remaining lines should be from buffer
        for row in range(10, rows):
            buffer_row = row - 10
            expected_line = widget._screen.buffer[buffer_row]
            expected_text = "".join(expected_line[col].data if expected_line[col].data else " " for col in range(cols)).rstrip()
            assert lines[row] == expected_text

    def test_copy_boundary_between_history_and_buffer(self):
        """AC: Selection at exact boundary between history and buffer works correctly."""
        widget = self._make_widget()

        # Create history
        for i in range(35):
            widget._on_pty_data(f"H{i:03d}\r\n".encode())

        # Write buffer
        widget._on_pty_data(b"B000\r\n")
        widget._on_pty_data(b"B001\r\n")

        # Scroll up by 3 lines
        # Rows 0-2: history
        # Rows 3+: buffer
        widget._scroll_offset = 3

        # Select rows 2-3 (boundary)
        widget._selection_start = (0, 2)
        widget._selection_end = (3, 3)

        text = widget._get_selected_text()
        lines = text.split("\n")

        assert len(lines) == 2

        # Row 2 should be from history
        history_len = len(widget._screen.history.top)
        history_idx = history_len - 3 + 2
        expected_row2 = widget._screen.history.top[history_idx]
        expected_text2 = "".join(expected_row2[col].data if expected_row2[col].data else " " for col in range(widget._cols)).rstrip()
        assert lines[0] == expected_text2

        # Row 3 should be from buffer[0]
        expected_row3 = widget._screen.buffer[0]
        expected_text3 = "".join(expected_row3[col].data if expected_row3[col].data else " " for col in range(4)).rstrip()
        assert lines[1][:4].rstrip() == expected_text3

    # -------------------------------------------------------------------------
    # Clipboard Integration Tests
    # -------------------------------------------------------------------------

    def test_clipboard_receives_history_text_when_scrolled(self):
        """AC: Clipboard contains exact text from history when copying while scrolled up."""
        from PyQt6.QtWidgets import QApplication

        widget = self._make_widget()

        # Create identifiable history
        for i in range(40):
            widget._on_pty_data(f"ClipHist{i:03d}\r\n".encode())

        # Scroll up by 7 lines
        widget._scroll_offset = 7

        # Select text from row 2 (in history)
        widget._selection_start = (0, 2)
        widget._selection_end = (10, 2)

        # Copy to clipboard
        widget._copy_selection()

        # Check clipboard
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()

        # Calculate expected text from history
        history_len = len(widget._screen.history.top)
        history_idx = history_len - 7 + 2
        expected_line = widget._screen.history.top[history_idx]
        expected_text = "".join(expected_line[col].data if expected_line[col].data else " " for col in range(11)).rstrip()

        assert clipboard_text == expected_text

    def test_clipboard_receives_buffer_text_when_at_bottom(self):
        """AC: Clipboard contains buffer text when copying at bottom (scroll_offset == 0)."""
        from PyQt6.QtWidgets import QApplication

        widget = self._make_widget()

        # Create history
        for i in range(30):
            widget._on_pty_data(f"Hist{i}\r\n".encode())

        # Write buffer
        widget._on_pty_data(b"ClipBuffer0\r\n")
        widget._on_pty_data(b"ClipBuffer1\r\n")

        # At bottom
        widget._scroll_offset = 0

        # Select from row 0
        widget._selection_start = (0, 0)
        widget._selection_end = (10, 0)

        # Copy to clipboard
        widget._copy_selection()

        # Check clipboard
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()

        # Should be from buffer
        expected_line = widget._screen.buffer[0]
        expected_text = "".join(expected_line[col].data if expected_line[col].data else " " for col in range(11)).rstrip()

        assert clipboard_text == expected_text

    def test_clipboard_receives_composite_text_when_selection_spans_regions(self):
        """AC: Clipboard contains composite text when selection spans history and buffer."""
        from PyQt6.QtWidgets import QApplication

        widget = self._make_widget()

        # Create history
        for i in range(45):
            widget._on_pty_data(f"H{i:02d}\r\n".encode())

        # Write buffer
        widget._on_pty_data(b"B00\r\n")
        widget._on_pty_data(b"B01\r\n")

        # Scroll up by 2 lines
        widget._scroll_offset = 2

        # Select from row 0 (history) to row 3 (buffer)
        widget._selection_start = (0, 0)
        widget._selection_end = (2, 3)

        # Copy to clipboard
        widget._copy_selection()

        # Check clipboard
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        lines = clipboard_text.split("\n")

        assert len(lines) == 4

        # First two lines from history
        history_len = len(widget._screen.history.top)
        for row in range(2):
            history_idx = history_len - 2 + row
            expected_line_obj = widget._screen.history.top[history_idx]
            expected_text = "".join(expected_line_obj[col].data if expected_line_obj[col].data else " " for col in range(widget._cols)).rstrip()
            assert lines[row] == expected_text

        # Last two lines from buffer
        for row in range(2, 4):
            buffer_row = row - 2
            expected_line_obj = widget._screen.buffer[buffer_row]
            if row == 3:
                # Last row, partial selection
                expected_text = "".join(expected_line_obj[col].data if expected_line_obj[col].data else " " for col in range(3)).rstrip()
                assert lines[row][:3].rstrip() == expected_text
            else:
                expected_text = "".join(expected_line_obj[col].data if expected_line_obj[col].data else " " for col in range(widget._cols)).rstrip()
                assert lines[row] == expected_text

    # -------------------------------------------------------------------------
    # Selection Coordinate Tests
    # -------------------------------------------------------------------------

    def test_selection_coordinates_remain_in_viewport_space(self):
        """AC: Selection coordinates (row, col) remain in viewport coordinate space (0 to _rows-1, 0 to _cols-1)."""
        widget = self._make_widget()

        # Create history
        for i in range(50):
            widget._on_pty_data(f"Line{i}\r\n".encode())

        # Scroll up
        widget._scroll_offset = 10

        # Set selection in viewport coordinates
        widget._selection_start = (5, 3)
        widget._selection_end = (15, 7)

        # Verify coordinates are in viewport space
        assert 0 <= widget._selection_start[1] < widget._rows
        assert 0 <= widget._selection_end[1] < widget._rows
        assert 0 <= widget._selection_start[0] < widget._cols
        assert 0 <= widget._selection_end[0] < widget._cols

        # Copy should work correctly
        text = widget._get_selected_text()
        assert isinstance(text, str)

    def test_copy_with_reversed_selection(self):
        """AC: Text extraction handles reversed selection (end before start)."""
        widget = self._make_widget()

        # Create history
        for i in range(40):
            widget._on_pty_data(f"Rev{i:03d}\r\n".encode())

        # Scroll up
        widget._scroll_offset = 5

        # Set reversed selection (end before start)
        widget._selection_start = (10, 3)
        widget._selection_end = (5, 2)

        # _normalized_selection should handle this
        text = widget._get_selected_text()
        assert isinstance(text, str)
        assert len(text) > 0

    # -------------------------------------------------------------------------
    # Formatting and Special Characters
    # -------------------------------------------------------------------------

    def test_copy_preserves_spaces_from_history(self):
        """AC: Copying from history preserves spaces correctly."""
        widget = self._make_widget()

        # Create history with spaces
        for i in range(35):
            widget._on_pty_data(f"A  B  C  {i:02d}\r\n".encode())

        # Scroll up
        widget._scroll_offset = 8

        # Select from row 4
        widget._selection_start = (0, 4)
        widget._selection_end = (11, 4)

        text = widget._get_selected_text()

        # Should preserve spaces
        history_len = len(widget._screen.history.top)
        history_idx = history_len - 8 + 4
        expected_line = widget._screen.history.top[history_idx]
        expected_text = "".join(expected_line[col].data if expected_line[col].data else " " for col in range(12)).rstrip()

        assert text == expected_text

    def test_copy_strips_trailing_spaces(self):
        """AC: Copying strips trailing spaces from each line."""
        widget = self._make_widget()

        # Create history
        for i in range(40):
            widget._on_pty_data(f"Text{i:02d}\r\n".encode())

        # Scroll up
        widget._scroll_offset = 5

        # Select entire row (including trailing spaces)
        widget._selection_start = (0, 2)
        widget._selection_end = (widget._cols - 1, 2)

        text = widget._get_selected_text()

        # Should be trimmed
        assert not text.endswith(" " * 10)

    # -------------------------------------------------------------------------
    # Regression Tests
    # -------------------------------------------------------------------------

    def test_existing_copy_behavior_at_bottom_unchanged(self):
        """Regression: Existing copy behavior when at bottom (_scroll_offset == 0) is preserved."""
        widget = self._make_widget()

        # Write current buffer WITHOUT filling history first
        # (so "Hello World" is at row 0 of the buffer)
        widget._on_pty_data(b"Hello World\r\n")
        widget._on_pty_data(b"Second Line\r\n")

        # At bottom
        widget._scroll_offset = 0

        # Select "World" from first line
        widget._selection_start = (6, 0)
        widget._selection_end = (10, 0)

        text = widget._get_selected_text()
        assert text == "World"

    def test_existing_multiline_copy_behavior_unchanged(self):
        """Regression: Existing multiline copy behavior when at bottom is preserved."""
        widget = self._make_widget()

        # Write buffer WITHOUT filling history first
        # (so "AAABBB" is at row 0 of the buffer)
        widget._on_pty_data(b"AAABBB\r\n")
        widget._on_pty_data(b"CCCDDD\r\n")

        # At bottom
        widget._scroll_offset = 0

        # Select from col 3 row 0 to col 2 row 1
        widget._selection_start = (3, 0)
        widget._selection_end = (2, 1)

        text = widget._get_selected_text()
        assert text == "BBB\nCCC"

    def test_no_selection_returns_empty_string(self):
        """Regression: No selection returns empty string."""
        widget = self._make_widget()

        # Create history
        for i in range(30):
            widget._on_pty_data(f"Text{i}\r\n".encode())

        # Scroll up
        widget._scroll_offset = 5

        # No selection
        widget._selection_start = None
        widget._selection_end = None

        text = widget._get_selected_text()
        assert text == ""

    # -------------------------------------------------------------------------
    # Visual Consistency Tests
    # -------------------------------------------------------------------------

    def test_copied_text_matches_visible_display(self):
        """AC: Text extraction correctly matches what paintEvent() displays."""
        widget = self._make_widget()

        # Create history with unique identifiers
        for i in range(50):
            widget._on_pty_data(f"UniqueHist{i:04d}\r\n".encode())

        # Write buffer
        for i in range(5):
            widget._on_pty_data(f"UniqueBuff{i}\r\n".encode())

        # Scroll up by 6 lines
        widget._scroll_offset = 6

        # Select row 0 (should be from history)
        widget._selection_start = (0, 0)
        widget._selection_end = (13, 0)

        # Get copied text
        copied_text = widget._get_selected_text()

        # Get what paintEvent would display for row 0
        screen = widget._screen
        history_len = len(screen.history.top)
        scroll_offset = widget._scroll_offset

        row = 0
        if scroll_offset > 0 and row < scroll_offset:
            history_idx = history_len - scroll_offset + row
            display_line = screen.history.top[history_idx]
        else:
            buffer_row = row - scroll_offset
            display_line = screen.buffer[buffer_row]

        expected_text = "".join(display_line[col].data if display_line[col].data else " " for col in range(14)).rstrip()

        assert copied_text == expected_text

    def test_copied_text_matches_highlighted_selection(self):
        """AC: Copied text exactly matches what is visually highlighted on screen."""
        widget = self._make_widget()

        # Create history
        for i in range(45):
            widget._on_pty_data(f"VisLine{i:03d}\r\n".encode())

        # Scroll up by 10 lines
        widget._scroll_offset = 10

        # Select rows 5-7 (all in history region)
        widget._selection_start = (0, 5)
        widget._selection_end = (9, 7)

        # Get copied text
        copied_text = widget._get_selected_text()
        copied_lines = copied_text.split("\n")

        # Verify each line matches what would be displayed
        screen = widget._screen
        history_len = len(screen.history.top)
        scroll_offset = widget._scroll_offset

        for i, row in enumerate(range(5, 8)):
            if scroll_offset > 0 and row < scroll_offset:
                history_idx = history_len - scroll_offset + row
                display_line = screen.history.top[history_idx]
            else:
                buffer_row = row - scroll_offset
                display_line = screen.buffer[buffer_row]

            if i == 0:
                # First row, starts at col 0
                expected = "".join(display_line[col].data if display_line[col].data else " " for col in range(widget._cols)).rstrip()
            elif i == len(copied_lines) - 1:
                # Last row, ends at col 9
                expected = "".join(display_line[col].data if display_line[col].data else " " for col in range(10)).rstrip()
            else:
                # Middle row
                expected = "".join(display_line[col].data if display_line[col].data else " " for col in range(widget._cols)).rstrip()

            assert copied_lines[i] == expected
