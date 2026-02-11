# Run Journal: Auto-approve

- **Run ID:** 2ccac665e288
- **Started:** 2026-02-11 01:43:23 UTC
- **Task:** Auto-approve
- **Ticket:** ticket:4 (ticket)

## Task Description

Create a project-level setting that determines whether to skip getting user approval for the requisite steps. Also allow individual tickets override this.
## Step: detect  (01:43:24)

See `levelup/project_context.md` for project details.
## Step: requirements  (01:44:58)

**Summary:** Add auto-approve functionality to skip user checkpoints at project and ticket levels
- 8 requirement(s)
- 6 assumption(s)
- 5 out-of-scope item(s)
- **Usage:** 93.2s
### Checkpoint: requirements

- **Decision:** approve
## Step: planning  (01:50:00)

**Approach:** Add auto-approve functionality at two levels: (1) project-level setting in PipelineSettings that applies to all checkpoints, and (2) per-ticket metadata that overrides the project setting. The implementation extends the existing checkpoint system in orchestrator.py to check auto-approve flags before prompting, logs auto-approved decisions to the journal, and adds GUI/CLI interfaces for managing ticket metadata. This design maintains backward compatibility while providing flexible checkpoint control.
- 14 implementation step(s)
- **Affected files:** src/levelup/config/settings.py, src/levelup/core/tickets.py, src/levelup/core/orchestrator.py, src/levelup/cli/app.py, src/levelup/gui/ticket_detail.py, tests/unit/test_config.py, tests/unit/test_ticket_metadata.py, tests/unit/test_auto_approve.py, tests/integration/test_auto_approve_pipeline.py, README.md, MEMORY.md
- **Risks:**
  - Ticket metadata format could break existing tickets if parser is not backward compatible - mitigate by ensuring parse_tickets() handles tickets without metadata gracefully
  - Auto-approve could bypass important security/review checks - mitigate by requiring explicit opt-in and documenting that require_checkpoints=False still controls whether checkpoints run at all
  - GUI ticket editing could corrupt metadata if not properly serialized - mitigate with thorough testing of metadata round-trip (parse → modify → serialize → parse)
  - Environment variable LEVELUP_PIPELINE__AUTO_APPROVE could be accidentally set globally - mitigate with clear documentation that auto-approve should be used carefully
  - Per-ticket auto-approve metadata could get out of sync with DB state - mitigate by always reading from markdown file as source of truth
  - Metadata format choice (HTML comment vs YAML frontmatter) affects readability - recommend HTML comment approach for better compatibility with markdown viewers
- **Usage:** 111.6s
## Step: test_writing  (01:56:30)

Wrote 7 test file(s):
- `tests/unit/test_auto_approve_settings.py` (new)
- `tests/unit/test_ticket_metadata.py` (new)
- `tests/unit/test_auto_approve_orchestrator.py` (new)
- `tests/unit/test_auto_approve_cli.py` (new)
- `tests/unit/test_tickets_cli_metadata.py` (new)
- `tests/integration/test_auto_approve_pipeline.py` (new)
- `tests/unit/test_gui_ticket_metadata.py` (new)
### Checkpoint: test_writing

- **Decision:** approve
## Step: coding  (02:05:51)

- **Code iterations:** 0
- **Test results:** 0 total, 0 failures, 0 errors (FAILED)
## Step: security  (02:07:40)

Step `security` completed.
- **Usage:** 107.1s
### Checkpoint: security

- **Decision:** approve
## Step: review  (02:15:23)

Found 11 issue(s):
- [WARNING] `tests/unit/test_gui_ticket_metadata.py`: The _on_save method in TicketDetailWidget does not save auto_approve metadata. It only emits a signal without passing metadata.
- [INFO] `tests/unit/test_ticket_metadata.py`: Test test_metadata_in_code_block_ignored may have false positives if the parser is changed to handle code blocks differently.
- [INFO] `tests/unit/test_auto_approve_orchestrator.py`: Mock setup uses side_effect=lambda name, ctx: ctx which doesn't properly simulate agent execution. This may hide bugs in context handling.
- [WARNING] `tests/unit/test_auto_approve_orchestrator.py`: Test expects mock_checkpoint.assert_not_called() but ticket lookup may fail silently and fall back to project settings, causing the test to pass for wrong reasons.
- [INFO] `tests/unit/test_tickets_cli_metadata.py`: Test test_tickets_update_with_metadata_flag tests a command that doesn't exist ('tickets update'). This is marked as testing an alternative design.
- [INFO] `tests/integration/test_auto_approve_pipeline.py`: Test test_mixed_tickets_with_different_metadata only runs one ticket and doesn't verify the second ticket's behavior.
- [WARNING] `tests/unit/test_auto_approve_cli.py`: Test verifies overrides dict but doesn't verify that the Orchestrator actually receives the correct settings object with auto_approve=True.
- [INFO] `tests/unit/test_gui_ticket_metadata.py`: Test test_save_preserves_other_metadata copies metadata dict without handling the case where auto_approve doesn't exist in original metadata.
- [INFO] `tests/unit/test_ticket_metadata.py`: The empty metadata block test (test_parse_empty_metadata_block) allows both None and {} as valid results, making behavior unclear.
- [WARNING] `tests/integration/test_auto_approve_pipeline.py`: Test test_ticket_metadata_highest_precedence patches tickets.read_tickets but the orchestrator calls it from within _should_auto_approve, which may not use the patched version if imports are cached.
- [INFO] `tests/integration/test_auto_approve_pipeline.py`: Test test_headless_without_auto_approve_creates_checkpoints creates a background thread that approves all checkpoints, adding unnecessary complexity.
