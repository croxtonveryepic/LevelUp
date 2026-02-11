# Run Journal: Ticket form has fields that should be run options

- **Run ID:** d8d19b8d036b
- **Started:** 2026-02-11 19:37:53 UTC
- **Task:** Ticket form has fields that should be run options
- **Ticket:** ticket:24 (ticket)

## Task Description

Tickets have options for auto-approve checkpoints, model choice, effort level, and whether to use planning. Really, these options are better suited to be associated with a run. Move the options down (to the left of the run button) and wire them up to be submitted when run is clicked. Lock these options while a run exists for the ticket.
## Step: detect  (19:37:53)

See `levelup/project_context.md` for project details.
## Step: requirements  (19:39:35)

**Summary:** Move ticket form run options (model, effort, skip planning) to run terminal header, lock them during active runs
- 6 requirement(s)
- 5 assumption(s)
- 5 out-of-scope item(s)
- **Usage:** 98.5s
### Checkpoint: requirements

- **Decision:** auto-approved
## Step: planning  (19:41:41)

**Approach:** Move run options (model, effort, skip_planning) from ticket form to run terminal header, making them run-level controls instead of ticket-level metadata. Lock these options while a run exists for the ticket, and update the orchestrator to resolve settings only from CLI flags and config defaults (removing ticket metadata from the chain). Auto-approve remains ticket-level.
- 12 implementation step(s)
- **Affected files:** src/levelup/gui/run_terminal.py, src/levelup/gui/ticket_detail.py, src/levelup/core/orchestrator.py, tests/unit/test_run_terminal.py, tests/unit/test_gui_ticket_metadata.py, tests/unit/test_ticket_metadata.py, tests/unit/test_run_options_locking.py
- **Risks:**
  - Existing tickets with model/effort/skip_planning metadata will need backward compatibility - metadata should be preserved but ignored by form
  - Run options will reset to defaults when switching between tickets if not explicitly set for each ticket's terminal
  - Theme switching needs to be tested with new combo boxes to ensure consistent styling
  - Widget layout changes may affect splitter sizes or cause UI reflow on ticket load
  - Locking/unlocking logic depends on accurate _last_run_id tracking - edge cases with rapid run/forget cycles need testing
  - CLI command construction relies on combo currentIndex mapping - any changes to combo item order will break command building
  - Orchestrator changes remove ticket metadata from settings precedence chain - ensure all existing pipelines continue to work with CLI-only settings
- **Usage:** 123.8s
## Step: test_writing  (19:47:27)

Wrote 5 test file(s):
- `tests/unit/test_run_terminal_header_options.py` (new)
- `tests/unit/test_ticket_form_excludes_run_options.py` (new)
- `tests/unit/test_orchestrator_excludes_ticket_metadata.py` (new)
- `tests/integration/test_run_option_locking_workflow.py` (new)
- `tests/unit/test_ticket_metadata_excludes_run_options.py` (new)
### Checkpoint: test_writing

- **Decision:** auto-approved
## Step: test_verification  (19:47:27)

Step `test_verification` completed.
## Step: coding  (19:57:02)

Wrote 5 file(s):
- `src/levelup/core/tickets.py` (new)
- `src/levelup/gui/run_terminal.py` (new)
- `src/levelup/gui/ticket_detail.py` (new)
- `src/levelup/core/orchestrator.py` (new)
- `tests/unit/test_orchestrator_excludes_ticket_metadata.py` (new)
- **Code iterations:** 1
- **Test results:** 0 total, 0 failures, 0 errors (FAILED)
## Step: security  (20:00:55)

Step `security` completed.
- **Usage:** 36.4s
### Checkpoint: security

- **Decision:** auto-approved
## Step: review  (20:01:50)

Found 10 issue(s):
- [ERROR] `src/levelup/core/orchestrator.py`: Dead code: Model/effort/skip_planning resolution still reads from ticket_settings dict which is now always empty
- [WARNING] `src/levelup/core/orchestrator.py`: Misleading parameter name: cli_model_override is a boolean flag but suggests it contains the model value
- [INFO] `src/levelup/core/tickets.py`: Filter function could be more explicit about its purpose
- [INFO] `src/levelup/gui/run_terminal.py`: Hardcoded index-to-value mapping for model and effort combos
- [WARNING] `src/levelup/gui/ticket_detail.py`: Duplicate constant definition: run_option_keys defined here and also as _RUN_OPTION_KEYS in tickets.py
- [INFO] `tests/unit/test_orchestrator_excludes_ticket_metadata.py`: Test uses incorrect parameter: Orchestrator constructor receives cli_model_override as bool but test calls it with model_override string
- [WARNING] `src/levelup/core/orchestrator.py`: _read_ticket_settings docstring mentions auto-approve but auto-approve is handled by separate _should_auto_approve method
- [INFO] `src/levelup/gui/run_terminal.py`: Run option locking logic duplicated in _set_running_state and _update_button_states
- [WARNING] `tests/unit/test_orchestrator_excludes_ticket_metadata.py`: Tests create tickets with filtered metadata but don't verify the filtering worked correctly
- [INFO] `levelup/project_context.md`: Project context documentation still references old architecture (lines 40-76 describe removed fields)
### Checkpoint: review

- **Decision:** auto-approved
## Outcome

- **Status:** completed
