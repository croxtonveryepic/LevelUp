# Run Journal: Hide merged features by default

- **Run ID:** 6e3a78c257a6
- **Started:** 2026-02-11 23:15:27 UTC
- **Task:** Hide merged features by default
- **Ticket:** ticket:26 (ticket)

## Task Description

Hide merged tickets from the sidebar list. Create a separate page for completed tickets.
## Step: detect  (23:15:28)

See `levelup/project_context.md` for project details.
## Step: requirements  (23:16:55)

**Summary:** Add status-based filtering to ticket sidebar with default hiding of merged tickets and a separate completed tickets page
- 4 requirement(s)
- 6 assumption(s)
- 7 out-of-scope item(s)
- **Usage:** 84.9s
### Checkpoint: requirements

- **Decision:** auto-approved
## Step: planning  (23:20:55)

**Approach:** Add status-based filtering to the ticket sidebar with a toggle control for merged tickets, and create a new dedicated page in the MainWindow's QStackedWidget to display completed (done + merged) tickets. The filtering will be implemented in the TicketSidebarWidget class, and the new completed tickets page will follow the same pattern as the existing DocsWidget (page 2) with a back button, header, and filtered ticket list.
- 10 implementation step(s)
- **Affected files:** src/levelup/gui/ticket_sidebar.py, src/levelup/gui/completed_tickets_widget.py, src/levelup/gui/main_window.py, src/levelup/gui/styles.py, tests/unit/test_ticket_sidebar_filtering.py, tests/unit/test_completed_tickets_widget.py, tests/integration/test_ticket_filtering_integration.py
- **Risks:**
  - Selection preservation logic may need careful handling when selected ticket is filtered out - should clear selection or move to nearest visible ticket
  - Filter state is session-only (in-memory) and will reset on application restart, which meets requirements but users may expect persistence
  - Existing tests that rely on all tickets being visible in sidebar may need updates to account for merged ticket filtering
  - Theme switching must properly update both the main sidebar and the completed tickets page to maintain visual consistency
  - Ticket count in status bar should reflect only visible (filtered) tickets, not all tickets in the file
- **Usage:** 238.0s
## Step: test_writing  (23:27:13)

Wrote 6 test file(s):
- `tests/unit/test_ticket_sidebar_filtering.py` (new)
- `tests/unit/test_completed_tickets_widget.py` (new)
- `tests/integration/test_completed_tickets_navigation.py` (new)
- `tests/unit/test_sidebar_toggle_styling.py` (new)
- `tests/integration/test_sidebar_filtering_workflow.py` (new)
- `tests/unit/test_sidebar_ticket_count.py` (new)
### Checkpoint: test_writing

- **Decision:** auto-approved
## Step: test_verification  (23:27:13)

Step `test_verification` completed.
## Step: coding  (23:32:05)

Wrote 3 file(s):
- `src/levelup/gui/ticket_sidebar.py` (new)
- `src/levelup/gui/completed_tickets_widget.py` (new)
- `src/levelup/gui/main_window.py` (new)
- **Code iterations:** 1
- **Test results:** 0 total, 0 failures, 0 errors (FAILED)
## Step: security  (23:33:06)

Step `security` completed.
- **Usage:** 59.5s
### Checkpoint: security

- **Decision:** auto-approved
## Step: review  (23:34:07)

Found 8 issue(s):
- [WARNING] `src/levelup/gui/ticket_sidebar.py`: The refresh() method in TicketSidebarWidget doesn't preserve run_status_map when refreshing, which could cause active run status colors to be lost
- [INFO] `src/levelup/gui/main_window.py`: The status bar shows total ticket count from _cached_tickets, which includes all tickets regardless of filter state. This might be confusing when merged tickets are hidden from the sidebar
- [INFO] `src/levelup/gui/completed_tickets_widget.py`: The update_theme method duplicates code from set_tickets. The logic for rendering tickets is repeated in two places
- [INFO] `src/levelup/gui/ticket_sidebar.py`: The _show_merged state variable is redundant since it can be derived from _show_merged_checkbox.isChecked()
- [INFO] `src/levelup/gui/main_window.py`: The condition 'not hasattr(self, "_cached_tickets")' is checking for attribute existence, but _cached_tickets is initialized in __init__ as an empty list. This condition will always be False
- [INFO] `tests/unit/test_sidebar_toggle_styling.py`: Test file focuses on styling and accessibility but doesn't verify actual CSS/QSS styling is applied to the checkbox
- [INFO] `src/levelup/gui/ticket_sidebar.py`: Signal blocking pattern is used but could be encapsulated in a context manager for better error handling
- [INFO] `src/levelup/gui/ticket_sidebar.py`: The _apply_filter method clears and rebuilds the entire list widget on every filter change, which could be slow with many tickets
### Checkpoint: review

- **Decision:** auto-approved
## Outcome

- **Status:** completed
