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
