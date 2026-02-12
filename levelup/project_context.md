# Project Context

- **Language:** python
- **Framework:** none
- **Test runner:** pytest
- **Test command:** pytest
- **Branch naming:** levelup/{task_title}
- **Placeholder substitution**: Support `{run_id}`, `{task_title}`, `{date}` placeholders in branch naming convention
- **Task title sanitization**: Convert to lowercase, replace spaces and special chars with hyphens, limit length (e.g., 50 chars)
- **Default convention**: Use `levelup/{run_id}` when field is missing (backward compatibility)
- **Resume/rollback**: Use stored convention from context to reconstruct branch name
- **Headless mode**: Skip prompt if running in headless mode; use existing convention or default

## Codebase Insights

### Project Structure

- **Source**: `src/levelup/` - main package directory
    - `agents/` - AI agent implementations (backend, recon, security, etc.)
    - `cli/` - Command-line interface commands
    - `config/` - Configuration loading and settings models
    - `core/` - Core functionality (instructions, tickets, orchestrator)
    - `detection/` - Project detection logic
    - `gui/` - PyQt6 GUI components
    - `state/` - SQLite state management
    - `tools/` - Agent tools for file operations

- **Tests**: `tests/`
    - `unit/` - Unit tests
    - `integration/` - Integration tests

### Git & Version Control

- **Worktrees**: Pipeline runs create git worktrees at `~/.levelup/worktrees/<run_id>/`
    - **Purpose**: Enable concurrent pipeline runs on different tickets without conflicts
    - **Location**: `~/.levelup/worktrees/<run_id>/`
    - Created in `Orchestrator._create_git_branch()` during pipeline initialization
    - Automatically cleaned up after successful/failed/aborted runs (but not paused)
    - Branch persists in main repo after worktree cleanup

- **Step Commits**: Each pipeline step gets a commit (when `create_git_branch: true`)
    - Stored in `ctx.step_commits` dict mapping step name to commit SHA
    - Commit messages follow pattern: `levelup({step_name}): {task_title}\n\nRun ID: {run_id}`
    - Created via `_git_step_commit()` in orchestrator

- **Branch Tracking**:
    - Branch naming convention stored in `ctx.branch_naming`
    - Branch name stored in ticket metadata as `branch_name` after completion
    - Pre-run SHA stored in `ctx.pre_run_sha` for rollback support

- **Git Operations**:
    - `_get_changed_files()` uses `git diff --name-only` to list changed files
    - GitPython library used for all git operations (gitpython>=3.1.0 in dependencies)
    - Main repository operations should run in project_path, not worktrees
    - Git diff operations: `repo.git.diff("--name-only", from_sha, to_sha)` returns list of changed files
    - Git diff with unified format: `repo.git.diff(from_sha, to_sha)` returns full diff output

### Pipeline Context Storage

- **PipelineContext** (`core/context.py`):
    - All pipeline state stored in Pydantic model
    - Includes: run_id, task, project info, agent outputs, git tracking, cost tracking
    - Serialized to JSON and stored in `runs.context_json` column in SQLite
    - Fields relevant to diff view:
        - `worktree_path`: Path to git worktree (if used)
        - `step_commits`: Dict mapping step names to commit SHAs
        - `pre_run_sha`: Starting commit SHA before run began
        - `project_path`: Main repository path

- **StateManager** (`state/manager.py`):
    - `update_run()` serializes full context via `ctx.model_dump_json()`
    - Context can be deserialized from `RunRecord.context_json`
    - Provides access to git information for any run

### GUI Architecture

- **Framework**: PyQt6-based desktop GUI
- **Main Window** (`gui/main_window.py`):
    - QStackedWidget with 4 pages:
        - Index 0: Runs table
        - Index 1: Ticket detail
        - Index 2: Documentation viewer
        - Index 3: Completed tickets viewer
    - Page navigation pattern: create widget → add to stack → connect back_clicked signal
    - Auto-refresh timer (REFRESH_INTERVAL_MS = 2000ms)

- **Key Display Widgets**:
    - `DocsWidget`: Uses QTextBrowser to display rendered markdown with theme CSS
    - `TerminalEmulatorWidget`: VT100 terminal with PTY backend
    - `TicketDetailWidget`: Vertical splitter with form (top) and terminal (bottom)
    - `CompletedTicketsWidget`: Filtered list view showing done/merged tickets

- **Theme System**:
    - Preferences: "light", "dark", "system" (default)
    - `update_theme(theme)` method propagates theme changes to child widgets
    - CSS templates for dark and light themes in DocsWidget
    - Color schemes for terminal emulator

- **Widget Communication**:
    - Signals: PyQt6 `pyqtSignal` for inter-component communication
    - Navigation: back_clicked signals return to runs table (page 0)
    - Object names set via `setObjectName()` for testing

### Text Display Patterns

- **QTextBrowser** (used in DocsWidget):
    - Read-only rich text display widget
    - Supports HTML rendering with custom CSS
    - `setHtml()` to set content, `setOpenLinks(False)` to handle links manually
    - `anchorClicked` signal for link handling
    - Suitable for displaying formatted text like diffs

- **Markdown Rendering**:
    - Uses `mistune>=3.0.0` library for markdown→HTML conversion
    - `render_markdown()` function in docs_widget.py
    - Fallback to escaped plaintext if mistune unavailable
    - `_wrap_html()` wraps body with theme-specific CSS

### Diff Display Considerations

- **Git diff output**: Can be obtained via GitPython's `repo.git.diff()`
- **Diff formats**:
    - `--name-only`: Just file names (used in `_get_changed_files()`)
    - Standard unified diff: Shows line-by-line changes with +/- markers
    - `--stat`: Summary statistics of changes
- **Syntax highlighting**: Could use HTML/CSS for diff coloring (red/green for -/+)
- **Per-commit vs branch**:
    - Per-commit: Use commit SHAs from `step_commits` dict
    - Whole branch: Diff from `pre_run_sha` to branch HEAD
- **Live updates**: Diff view needs to refresh while run is in progress

### Testing Patterns

- Unit tests use pytest with PyQt6 fixtures
- `_can_import_pyqt6()` check and `@pytest.mark.skipif` decorator
- Mock state manager using `MagicMock(spec=StateManager)`
- Button state tests verify enabled/disabled states
- Integration tests use temporary directories (`tmp_path` fixture)
- Test files follow pattern: `test_<component>.py` or `test_<component>_<feature>.py`
- Widget tests: check structure (findChild), signals (connect to lambda), and behavior
- Theme tests: verify color codes in HTML output
- pytest markers: `@pytest.mark.regression` for exhaustive tests, `@pytest.mark.smoke` for core tests

### Key Conventions

- Windows paths: Use `.replace("\\", "/")` in test assertions
- Test classes named `Test*` trigger pytest collection warnings (expected)
- SQLite WAL mode for multi-process access
- Git worktrees for concurrent runs at `~/.levelup/worktrees/<run_id>/`
- Parent widgets pass theme to child widgets during construction
- Theme updates propagate via `update_theme(theme)` method
- Widget navigation: create → add to stack → connect signals
- Back buttons return to index 0 (runs table)
