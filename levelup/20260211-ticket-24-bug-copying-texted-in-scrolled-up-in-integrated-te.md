# Run Journal: Bug: Copying texted in scrolled-up in integrated terminal

- **Run ID:** 6f1d48fc4c74
- **Started:** 2026-02-11 21:04:52 UTC
- **Task:** Bug: Copying texted in scrolled-up in integrated terminal
- **Ticket:** ticket:24 (ticket)

## Task Description

When scrolled up in an integrated terminal, highlighting text and copying it to clipboard actually copies the text in the same relative position (area of the screen) at the very bottom of the terminal output instead of what appears to be highlighted.
## Step: detect  (21:04:53)

See `levelup/project_context.md` for project details.
## Step: requirements  (21:07:14)

**Summary:** Fix terminal text copying bug when scrolled up - clipboard copies wrong text from buffer instead of visible history
- 2 requirement(s)
- 5 assumption(s)
- 7 out-of-scope item(s)
- **Usage:** 140.0s
### Checkpoint: requirements

- **Decision:** auto-approved
## Step: planning  (21:09:39)

**Approach:** Fix the terminal text copying bug by updating the _get_selected_text() method to use the same composite view logic as paintEvent() when scroll_offset > 0. This involves reading from history.top for rows < scroll_offset and from buffer for rows >= scroll_offset, matching the rendering behavior. Add comprehensive unit tests to verify correct copying behavior in all scroll states.
- 2 implementation step(s)
- **Affected files:** src/levelup/gui/terminal_emulator.py, tests/unit/test_terminal_scrollback_copy.py
- **Risks:**
  - Edge case: If scroll_offset exceeds history length, index calculation could be out of bounds - need to handle gracefully like paintEvent does
  - Edge case: Empty history with scroll_offset > 0 needs careful handling to avoid index errors
  - Multi-line selections spanning both history and buffer regions require correct composite text assembly
  - Existing tests in test_terminal_emulator.py test _get_selected_text() at scroll_offset=0, must ensure backward compatibility
- **Usage:** 142.6s
## Step: test_writing  (21:12:21)

Wrote 1 test file(s):
- `tests/unit/test_terminal_scrollback_copy.py` (new)
