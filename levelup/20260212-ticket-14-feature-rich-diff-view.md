# Run Journal: Feature: Rich diff view

- **Run ID:** 0945b8557202
- **Started:** 2026-02-12 17:50:44 UTC
- **Task:** Feature: Rich diff view
- **Ticket:** ticket:14 (ticket)

## Task Description

Users should be able to review changes from within the LevelUp GUI. Changes should be observable on a per-commit basis (so each step can be inspected individually) or the whole branch as a whole. Make sure this works while a run is in progress as well.
## Step: detect  (17:50:44)

See `levelup/project_context.md` for project details.
## Step: requirements  (17:53:02)

**Summary:** Add a rich diff view widget to the LevelUp GUI that allows users to review code changes from pipeline runs on a per-commit basis (individual steps) or for the entire branch, with live updates during active runs
- 8 requirement(s)
- 5 assumption(s)
- 7 out-of-scope item(s)
- **Usage:** 135.2s
### Checkpoint: requirements

- **Decision:** auto-approved
## Step: planning  (17:54:54)

**Approach:** Add a new DiffViewWidget (page 4) to MainWindow's stacked widget that displays git diffs for pipeline runs. The widget will follow existing GUI patterns (QTextBrowser for HTML rendering, theme support, back button). It will extract PipelineContext from RunRecord.context_json to access step commits and pre_run_sha, then use GitPython to generate diffs. Navigation will be added from both the runs table context menu and the RunTerminalWidget header. Live updates will be handled via MainWindow's existing refresh timer.
- 8 implementation step(s)
- **Affected files:** src/levelup/gui/diff_view_widget.py, src/levelup/gui/main_window.py, src/levelup/gui/run_terminal.py, tests/unit/test_diff_view_widget.py, tests/integration/test_diff_view_workflow.py
- **Risks:**
  - Git operations may fail if repository is in an inconsistent state or commits are missing
  - Worktree cleanup may cause SHA references to become invalid if not handled properly
  - Large diffs could cause performance issues in QTextBrowser rendering
  - Live refresh during active runs may cause flickering if not debounced properly
  - Context deserialization from JSON may fail for old run records without required fields
- **Usage:** 110.2s
