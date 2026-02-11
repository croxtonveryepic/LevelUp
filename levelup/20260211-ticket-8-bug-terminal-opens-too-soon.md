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
## Step: test_writing  (02:02:06)

Wrote 4 test file(s):
- `tests/unit/test_delayed_terminal_initialization.py` (new)
- `tests/unit/test_run_terminal_show_event.py` (new)
- `tests/unit/test_terminal_isolation_integration.py` (new)
- `tests/unit/test_terminal_functionality_preservation.py` (new)
### Checkpoint: test_writing

- **Decision:** approve
## Step: coding  (02:15:24)

Wrote 1 file(s):
- `src/levelup/gui/run_terminal.py` (new)
- **Code iterations:** 1
- **Test results:** 0 total, 0 failures, 0 errors (FAILED)
## Step: security  (02:18:24)

Step `security` completed.
- **Usage:** 49.2s
### Checkpoint: security

- **Decision:** approve
## Step: review  (02:20:29)

Found 9 issue(s):
- [WARNING] `src/levelup/gui/run_terminal.py`: Command injection vulnerability via os.system() with user-controlled PID
- [WARNING] `src/levelup/gui/run_terminal.py`: Direct access to private StateManager._conn() method violates encapsulation
- [INFO] `src/levelup/gui/run_terminal.py`: Accessing internal _shell_started flag from ticket_detail.py breaks encapsulation
- [INFO] `src/levelup/gui/run_terminal.py`: Empty showEvent implementation could be confusing
- [INFO] `src/levelup/gui/ticket_detail.py`: Race condition: checking _shell_started before calling close_shell()
- [INFO] `tests/unit/test_delayed_terminal_initialization.py`: PtyBackend is mocked at import time, which may cause issues if tests run in parallel
- [INFO] `src/levelup/gui/run_terminal.py`: Polling every 1 second for run status could be optimized
- [WARNING] `src/levelup/gui/run_terminal.py`: Fallback run detection by project_path can return wrong run if multiple runs exist
- [INFO] `src/levelup/gui/run_terminal.py`: _ensure_shell method is idempotent but lacks error handling
### Checkpoint: review

- **Decision:** approve
## Outcome

- **Status:** completed
