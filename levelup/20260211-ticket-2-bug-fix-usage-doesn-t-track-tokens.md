# Run Journal: Bug fix: usage doesn't track tokens

- **Run ID:** 70249a0e56db
- **Started:** 2026-02-11 01:43:00 UTC
- **Task:** Bug fix: usage doesn't track tokens
- **Ticket:** ticket:2 (ticket)

## Task Description

LevelUp tracks usage as in time consumed, but it should also provide information about token input and output.
## Step: detect  (01:43:00)

See `levelup/project_context.md` for project details.
## Step: requirements  (01:44:49)

**Summary:** Add token usage tracking (input/output tokens) to the GUI dashboard and database, complementing the existing CLI token display
- 5 requirement(s)
- 5 assumption(s)
- 5 out-of-scope item(s)
- **Usage:** 107.2s
### Checkpoint: requirements

- **Decision:** approve
## Step: planning  (01:49:48)

**Approach:** Add input_tokens and output_tokens columns to the database schema (migration v5), update RunRecord model to include token fields with defaults, modify StateManager.update_run() to calculate and persist total tokens from ctx.step_usage, and update GUI main window to display token information in both the runs table and detail view. This complements the existing CLI token display without breaking backward compatibility.
- 8 implementation step(s)
- **Affected files:** src/levelup/state/db.py, src/levelup/state/models.py, src/levelup/state/manager.py, src/levelup/gui/main_window.py, tests/unit/test_cost_tracking.py
- **Risks:**
  - Migration must be idempotent and handle existing databases gracefully
  - Token calculation logic must handle cases where step_usage dict is empty or missing
  - GUI table column addition may affect layout and require header resize mode adjustments
  - RunRecord with zero tokens should display 'N/A' to distinguish from unavailable data
  - Database queries should remain performant with additional columns
  - Existing tests in test_cost_tracking.py must continue to pass with schema v5
- **Usage:** 93.7s
## Step: test_writing  (01:52:24)

No test files written.
