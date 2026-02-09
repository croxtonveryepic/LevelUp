# Run Journal: Make previous runs removeable

- **Run ID:** 6be0c44d64f0
- **Started:** 2026-02-09 20:08:21 UTC
- **Task:** Make previous runs removeable

## Task Description

Add a command called forget to remove previous runs (to clean up the resume menu). Like resume, there should be a command to delete by id and an interactive option. Additionally, levelup forget --nuke should delete all previous runs.
## Step: detect  (20:08:21)

See `levelup/project_context.md` for project details.
## Step: requirements  (20:10:12)

**Summary:** Add a 'forget' command to remove previous runs from the state database, enabling cleanup of the resume menu with support for deleting by ID, interactive selection, and bulk deletion.
- 6 requirement(s)
- 6 assumption(s)
- 5 out-of-scope item(s)
- **Usage:** 108.7s
### Checkpoint: requirements

- **Decision:** approve
## Step: planning  (20:12:20)

**Approach:** Implement a 'forget' command following the existing 'resume' pattern: support explicit run-id argument, interactive picker when no argument provided, and --nuke flag for bulk deletion. Reuse existing StateManager.delete_run() method and adapt pick_resumable_run() helper for the forget use case. Add comprehensive tests following test_resume_rollback.py patterns.
- 4 implementation step(s)
- **Affected files:** src/levelup/cli/prompts.py, src/levelup/cli/app.py, tests/unit/test_cli_forget.py, README.md
- **Risks:**
  - Interactive picker might need to show all runs (not just failed/aborted) which differs from resume picker - need to ensure proper filtering
  - Confirmation prompts are critical for --nuke flag to prevent accidental data loss
  - Need to handle empty database case gracefully in all three modes
  - Windows path handling in tests requires backslash normalization
- **Usage:** 84.8s
## Step: test_writing  (20:16:36)

Wrote 3 test file(s):
- `tests/unit/test_cli_forget.py` (new)
- `tests/unit/test_prompts_forget.py` (new)
- `tests/integration/test_forget_integration.py` (new)
