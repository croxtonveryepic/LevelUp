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
