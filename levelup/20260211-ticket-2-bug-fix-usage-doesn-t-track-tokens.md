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
### Checkpoint: test_writing

- **Decision:** approve
## Step: coding  (02:01:17)

Wrote 6 file(s):
- `src/levelup/state/db.py` (new)
- `src/levelup/state/models.py` (new)
- `src/levelup/state/manager.py` (new)
- `src/levelup/gui/main_window.py` (new)
- `tests/unit/test_state_db.py` (new)
- `tests/unit/test_cost_tracking.py` (new)
- **Code iterations:** 1
- **Test results:** 0 total, 0 failures, 0 errors (FAILED)
## Step: security  (02:01:56)

Step `security` completed.
- **Usage:** 37.3s
### Checkpoint: security

- **Decision:** approve
## Step: review  (02:05:55)

Found 6 issue(s):
- [WARNING] `tests/unit/test_state_db.py`: Test class name 'TestMigrationV4' is misleading - it actually tests migration to v5
- [WARNING] `tests/unit/test_state_db.py`: Test 'test_runs_table_columns' doesn't verify all columns exist after migration v5
- [INFO] `src/levelup/state/manager.py`: Token aggregation logic could be extracted to a helper method for reusability
- [INFO] `src/levelup/gui/main_window.py`: Token formatting logic is duplicated between _update_table and _view_details
- [INFO] `src/levelup/state/db.py`: CURRENT_SCHEMA_VERSION constant could have a docstring explaining the versioning scheme
- [INFO] `src/levelup/core/journal.py`: Journal logs total tokens but doesn't break down into input/output like the GUI does
### Checkpoint: review

- **Decision:** approve
## Outcome

- **Status:** completed
