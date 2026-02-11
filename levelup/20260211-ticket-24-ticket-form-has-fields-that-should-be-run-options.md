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
