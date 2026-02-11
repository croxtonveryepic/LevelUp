# Run Journal: Bug: Can't scroll up in integrated terminal

- **Run ID:** 41f7a25b6d3f
- **Started:** 2026-02-11 04:23:46 UTC
- **Task:** Bug: Can't scroll up in integrated terminal
- **Ticket:** ticket:10 (ticket)

## Task Description

Users report that they can't scroll up in integrated terminals to review each step.
## Step: detect  (04:23:46)

See `levelup/project_context.md` for project details.
## Step: requirements  (04:25:19)

**Summary:** Fix terminal emulator scrollback to display historical lines when scrolling up
- 3 requirement(s)
- 5 assumption(s)
- 6 out-of-scope item(s)
- **Usage:** 91.9s
### Checkpoint: requirements

- **Decision:** approve
## Step: planning  (04:43:02)

**Approach:** Modify TerminalEmulatorWidget.paintEvent() to composite historical lines from screen.history.top with current buffer lines when _scroll_offset > 0. The implementation will access history lines in reverse order (newest first) and display them at the top of the viewport, with remaining rows showing current buffer lines. All existing scrolling behaviors (wheelEvent, keyPressEvent snap-to-bottom, cursor hiding) are already correct and will be preserved.
- 2 implementation step(s)
- **Affected files:** src/levelup/gui/terminal_emulator.py, tests/unit/test_terminal_scrollback_display.py
- **Risks:**
  - History lines in pyte.HistoryScreen.history.top are stored as deques of line objects - must verify the exact structure matches screen.buffer line format
  - Selection logic (_cell_in_selection, _get_selected_text) assumes rows map to screen.buffer indices - needs adjustment to handle history-composite viewport
  - Edge case: when history has fewer lines than scroll_offset, viewport should show all available history then fill remaining rows with buffer lines
  - Performance: accessing history.top deque elements by index may be O(n) for deque - consider converting to list if performance issues arise
- **Usage:** 259.7s
## Step: test_writing  (04:47:44)

Wrote 2 test file(s):
- `tests/unit/test_terminal_scrollback_display.py` (new)
- `tests/unit/test_terminal_scrollback_rendering.py` (new)
### Checkpoint: test_writing

- **Decision:** approve
## Step: test_verification  (04:48:02)

Step `test_verification` completed.
## Step: coding  (04:49:47)

Wrote 1 file(s):
- `src/levelup/gui/terminal_emulator.py` (new)
- **Code iterations:** 1
- **Test results:** 0 total, 0 failures, 0 errors (FAILED)
## Step: security  (04:54:20)

Step `security` completed.
- **Usage:** 69.5s
### Checkpoint: security

- **Decision:** approve
## Step: review  (04:55:28)

Found 10 issue(s):
- [ERROR] `src/levelup/gui/terminal_emulator.py`: Incorrect scrollback compositing logic when scroll_offset >= _rows. When scroll_offset equals or exceeds the viewport height, ALL viewport rows should display history, but the current logic at line 536 only displays history for rows < scroll_offset.
- [CRITICAL] `src/levelup/gui/terminal_emulator.py`: _get_selected_text() only reads from screen.buffer and does not account for scroll_offset. When user selects text while scrolled up viewing history, the selection will copy from the wrong lines (current buffer instead of displayed history).
- [WARNING] `src/levelup/gui/terminal_emulator.py`: Fallback to screen.buffer[0] when history index is out of bounds may display incorrect content. If history is empty or insufficient, falling back to the first buffer line could show misleading content instead of an empty line.
- [WARNING] `src/levelup/gui/terminal_emulator.py`: Fallback to screen.buffer[-1] when buffer_row is out of bounds may display incorrect content. Similar to the history fallback issue, using the last buffer line as a fallback could be misleading.
- [WARNING] `src/levelup/gui/terminal_emulator.py`: paintEvent() renders every cell on every frame. With scroll offset calculation happening inside the loop, this could be inefficient for large terminals (e.g., 80x50 = 4000 cells per frame).
- [INFO] `tests/unit/test_terminal_scrollback_display.py`: Helper method _get_displayed_lines() duplicates the paintEvent rendering logic. This creates maintenance burden - if paintEvent changes, tests must be updated too.
- [INFO] `tests/unit/test_terminal_scrollback_display.py`: Many tests only verify that indices are in bounds without actually checking that the correct content is displayed. Tests like test_paintevent_accesses_history_when_scrolled_up verify 'expected_history_idx' is valid but don't verify the actual line content matches expectations.
- [WARNING] `src/levelup/gui/terminal_emulator.py`: wheelEvent() clamps scroll_offset to len(history.top) but doesn't account for viewport height. When history is shorter than viewport, scrolling could result in gaps or incorrect display.
- [INFO] `tests/unit/test_terminal_scrollback_rendering.py`: test_terminal_scrollback_rendering.py and test_terminal_scrollback_display.py have significant overlap in test coverage. Both test files verify similar scrollback behaviors with slightly different test case names.
- [WARNING] `src/levelup/gui/terminal_emulator.py`: Array index access in _get_selected_text() at line 768 (screen.buffer[row]) could raise IndexError if row >= len(screen.buffer). The selection coordinates are in viewport space but buffer access assumes they're valid buffer indices.
