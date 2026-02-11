# Run Journal: Bug: Terminal opens too soon

- **Run ID:** 08585e03d560
- **Started:** 2026-02-11 01:51:39 UTC
- **Task:** Bug: Terminal opens too soon
- **Ticket:** ticket:8 (ticket)

## Task Description

Integrated terminal should only be initialized when the ticket is run.
## Step: detect  (01:51:39)

See `levelup/project_context.md` for project details.
## Step: requirements  (01:52:49)

**Summary:** Delay terminal initialization until Run button is clicked
- 4 requirement(s)
- 4 assumption(s)
- 4 out-of-scope item(s)
- **Usage:** 68.3s
### Checkpoint: requirements

- **Decision:** approve
## Step: planning  (01:56:54)

**Approach:** Remove automatic shell initialization from RunTerminalWidget.showEvent() and ensure shell is only initialized when Run or Resume buttons are clicked. The fix is straightforward: remove the _ensure_shell() call from showEvent() while keeping it in start_run() and _on_resume_clicked(). Add tests to verify the delayed initialization behavior.
- 5 implementation step(s)
- **Affected files:** src/levelup/gui/run_terminal.py, tests/unit/test_run_terminal.py
- **Risks:**
  - If any code path calls showEvent() expecting the shell to be initialized, that code may break. However, review shows start_run() and _on_resume_clicked() both call _ensure_shell() explicitly, so this should be safe.
  - Tests may fail if they rely on the old behavior of shell being initialized on widget visibility. However, test review shows that integration tests already mock the PtyBackend, so they should not be affected.
  - The terminal widget may be shown multiple times (when switching between tickets), but this is OK because showEvent() will now be a no-op and _ensure_shell() is idempotent.
- **Usage:** 82.7s
