# Run Journal: Bug: Resume button always disabled

- **Run ID:** 903396ec405f
- **Started:** 2026-02-11 01:54:26 UTC
- **Task:** Bug: Resume button always disabled
- **Ticket:** ticket:9 (ticket)

## Task Description

The intended use of the resume button is to resume the run pipeline on tickets that have been paused. Review what the button currently does and when it is enabled to ensure correct functionality. Also, disable the run button while there is a pipeline that can be resumed.
## Step: detect  (01:54:26)

See `levelup/project_context.md` for project details.
## Step: requirements  (01:55:46)

**Summary:** Fix resume button state logic and ensure run button is disabled when a resumable run exists
- 4 requirement(s)
- 6 assumption(s)
- 7 out-of-scope item(s)
- **Usage:** 78.0s
### Checkpoint: requirements

- **Decision:** approve
## Step: planning  (01:57:56)

**Approach:** Fix the run and resume button state logic in RunTerminalWidget by updating both _set_running_state() and _update_button_states() methods to check for resumable runs before enabling the run button. The run button should be disabled when a resumable run exists (status: failed, aborted, or paused), and only be enabled when not running AND (no run exists OR run is not resumable). This ensures users must either resume or forget the existing run before starting a new one.
- 5 implementation step(s)
- **Affected files:** src/levelup/gui/run_terminal.py, tests/unit/test_run_terminal_button_states.py, tests/integration/test_run_resume_workflow.py
- **Risks:**
  - The enable_run() method is called from ticket_detail.py and may need coordination to ensure consistent behavior across both widgets
  - Button state changes during polling (_poll_for_run_id) may interact with manual state updates in complex ways
  - The _wire_existing_run() method in ticket_detail.py calls _update_button_states(), so changes must be compatible with that flow
  - Testing requires mocking PyQt6 components and StateManager interactions which may be complex
  - Changes affect critical user workflow (starting runs) so thorough testing is essential
- **Usage:** 81.6s
