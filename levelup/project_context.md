# Project Context

- **Language:** python
- **Framework:** none
- **Test runner:** pytest
- **Test command:** pytest
- **Branch naming:** levelup/{run_id}
- **Placeholder substitution**: Support `{run_id}`, `{task_title}`, `{date}` placeholders in branch naming convention
- **Task title sanitization**: Convert to lowercase, replace spaces and special chars with hyphens, limit length (e.g., 50 chars)
- **Default convention**: Use `levelup/{run_id}` when field is missing (backward compatibility)
- **Resume/rollback**: Use stored convention from context to reconstruct branch name
- **Headless mode**: Skip prompt if running in headless mode; use existing convention or default

## Codebase Insights

### Project Structure

- `src/levelup/` - Main source code directory
    - `agents/` - Claude AI agent implementations for different pipeline steps
    - `cli/` - CLI commands and display utilities
    - `config/` - Configuration and settings (Pydantic models)
    - `core/` - Core orchestration, pipeline, checkpoints, tickets
    - `detection/` - Project detection (language, framework, test runner)
    - `gui/` - PyQt6-based dashboard interface
    - `state/` - SQLite state management for multi-instance coordination
    - `tools/` - Agent tools (file I/O, shell, test runner)
- `tests/` - Test suite with unit and integration tests

### Usage Tracking Architecture

- **Backend tracking**: Both `ClaudeCodeBackend` and `AnthropicSDKBackend` track usage via `AgentResult`
    - `AgentResult` dataclass (`agents/backend.py`) contains: `input_tokens`, `output_tokens`, `cost_usd`, `duration_ms`, `num_turns`
    - `ToolLoopResult` dataclass (`agents/llm_client.py`) tracks tokens accumulated across LLM API calls
- **Context storage**: `PipelineContext` (`core/context.py`) stores usage data:
    - `step_usage: dict[str, StepUsage]` - per-step metrics
    - `total_cost_usd: float` - cumulative cost across all steps
    - `StepUsage` model tracks: `cost_usd`, `input_tokens`, `output_tokens`, `duration_ms`, `num_turns`
- **Orchestrator**: `_capture_usage()` method (`core/orchestrator.py`) captures agent results into context
    - Called after each agent run at line 604
    - Extracts token counts from `AgentResult` and creates `StepUsage` objects
    - Accumulates total cost: `ctx.total_cost_usd += usage.cost_usd`
    - Stores per-step usage: `ctx.step_usage[agent_name] = usage`
- **Journal**: `RunJournal` (`core/journal.py`) logs usage per step and total cost in markdown
- **CLI display**: `print_pipeline_summary()` (`cli/display.py`) shows:
    - Total tokens summary (lines 260-264): formats as `{total:,} ({input:,} in / {output:,} out)`
    - Per-step cost breakdown table with tokens column (lines 268-281)
- **Database**: `runs` table has `total_cost_usd` column but NO token columns (as of v4)
- **GUI**: Main window (`gui/main_window.py`) shows run table with columns: Run ID, Task, Project, Status, Step, Started
    - Does NOT display cost or token information in the table (line 38: `COLUMNS` list)
    - Detail view (lines 448-465) shows run metadata but omits cost and token data
    - `RunRecord` model (`state/models.py`) only has `total_cost_usd` field, no token fields

### Database Schema Management

- **Current version**: v4 (`CURRENT_SCHEMA_VERSION` in `state/db.py` line 44)
- **Migration system**:
    - List of `(target_version, sql)` tuples in `MIGRATIONS` (lines 47-82)
    - `_run_migrations()` function applies pending migrations sequentially (lines 94-111)
    - Migration v1: Created schema_version table
    - Migration v2: Added `total_cost_usd REAL DEFAULT 0` column
    - Migration v3: Added `pause_requested INTEGER DEFAULT 0` column
    - Migration v4: Added `ticket_number INTEGER` column and index
- **Schema initialization**: `init_db()` creates base schema then runs migrations
- **Migration patterns**: Each migration includes version table update at the end

### StateManager Data Flow

- **Registration**: `register_run()` (lines 65-97) inserts new run, extracts ticket number from context
- **Updates**: `update_run()` (lines 99-128) persists context changes including:
    - Status, step, error message
    - Language, framework, test runner
    - `context_json` - serialized full context (includes step_usage dict)
    - `total_cost_usd` - extracted from ctx.total_cost_usd (line 121)
    - Does NOT extract input_tokens/output_tokens (would need to sum from ctx.step_usage)
- **Retrieval**: `get_run()` returns `RunRecord` Pydantic model from DB row

### TDD Pipeline Architecture

- **Pipeline definition**: `src/levelup/core/pipeline.py` contains `DEFAULT_PIPELINE` with ordered `PipelineStep` objects
- **Current pipeline flow**:
    1. `detect` - Project detection (StepType.DETECTION)
    2. `requirements` - Requirements agent (StepType.AGENT, checkpoint_after=True)
    3. `planning` - Planning agent (StepType.AGENT)
    4. `test_writing` - Test writer agent (StepType.AGENT, checkpoint_after=True)
    5. `coding` - Coder agent (StepType.AGENT)
    6. `security` - Security agent (StepType.AGENT, checkpoint_after=True)
    7. `review` - Review agent (StepType.AGENT, checkpoint_after=True)
- **Step execution**: `Orchestrator._execute_steps()` iterates through pipeline steps
- **Agents**:
    - `TestWriterAgent` (`agents/test_writer.py`) - Writes tests (TDD red phase), optionally runs tests via Bash to confirm they fail
    - `CodeAgent` (`agents/coder.py`) - Implements code and iterates until tests pass (TDD green phase)
    - Both agents have system prompts, allowed tools, and run methods that return `(PipelineContext, AgentResult)`
- **Checkpoints**: User review points defined by `checkpoint_after=True` on pipeline steps
    - Interactive mode: `run_checkpoint()` displays content and gets user decision
    - Headless mode: Polls DB for checkpoint decision via `_wait_for_checkpoint_decision()`
    - Display logic: `build_checkpoint_display_data()` and `_display_checkpoint_content()` in `checkpoint.py`
- **Test execution**:
    - Agents use `Bash` tool to run test commands during their workflows
    - `TestRunnerTool` (`tools/test_runner.py`) can be used by agents to run tests with structured parsing
    - Final test results stored in `PipelineContext.test_results` (list of `TestResult` objects)

### Agent Architecture

- **BaseAgent**: Abstract base class in `agents/base.py` with required methods:
    - `get_system_prompt(ctx)` - Returns system prompt string
    - `get_allowed_tools()` - Returns list of tool names
    - `run(ctx)` - Executes agent work, returns `(PipelineContext, AgentResult)`
- **Agent Registration**: Agents registered in `Orchestrator._register_agents()` method:
    - Creates instances with `backend` and `project_path` parameters
    - Stored in `self._agents` dict with string keys (agent names)
    - Must match `agent_name` field in pipeline steps
- **Backend Types**:
    - `ClaudeCodeBackend` - Spawns `claude -p` subprocesses
    - `AnthropicSDKBackend` - Uses Anthropic SDK with tool registry
    - Both backends implement `run_agent()` method that returns `AgentResult`
- **AgentResult**: Dataclass containing:
    - `text` - Agent response text
    - `cost_usd`, `input_tokens`, `output_tokens` - Usage metrics
    - `duration_ms`, `num_turns` - Timing and interaction metrics

### PipelineContext Data Model

- **Core fields**:
    - `run_id`, `started_at`, `task`, `project_path`
    - `language`, `framework`, `test_runner`, `test_command`, `branch_naming`
    - `requirements`, `plan`, `test_files`, `code_files`, `test_results`, `review_findings`
    - `status`, `current_step`, `code_iteration`, `error_message`
    - `step_usage` (dict[str, StepUsage]) - Tracks cost/tokens per step
- **TestResult model**: Contains `passed`, `total`, `failures`, `errors`, `output`, `command`
- Context flows through entire pipeline, agents modify and return it

### Test Runner and Verification

- **TestRunnerTool** (`tools/test_runner.py`):
    - `execute()` method runs test command and returns string summary
    - `run_and_parse()` method returns structured `TestResult` object
    - Parses test output for common formats (pytest, jest, mocha)
    - Supports timeout configuration (default 120s)
- **Test result parsing**: `_parse_test_output()` extracts pass/fail counts
    - Uses `_extract_number_before()` for regex-based parsing
    - Handles pytest format: "3 passed, 2 failed" or "4 passed, 1 failed, 2 error"
- **Subprocess usage**: Tests run via `subprocess.run()` with shell=True
    - Exit code 0 = passed, non-zero = failed
    - Captures stdout and stderr for output analysis

### Display and CLI

- **Step headers**: `print_step_header(step_name, description)` in `cli/display.py`
    - Called before each step in `Orchestrator._execute_steps()`
    - Format: `[bold cyan]>>> {step_name}[/bold cyan]: {description}`
- **Success/error messages**: `print_success()` and `print_error()` functions
- **Rich console**: Uses rich library for formatted output
- Checkpoint display uses `build_checkpoint_display_data()` to serialize step content

### Configuration Architecture

- **Pydantic-based settings** in `src/levelup/config/settings.py`:
    - `LLMSettings` - LLM backend configuration
    - `ProjectSettings` - Project-specific settings (includes `tickets_file` path)
    - `PipelineSettings` - Pipeline behavior settings (includes `require_checkpoints: bool = True`)
    - `GUISettings` - GUI theme configuration
    - `LevelUpSettings` - Root settings class with nested models
- **Layered configuration** in `src/levelup/config/loader.py`:
    - Priority: defaults → file → env vars → CLI overrides
    - Uses `_deep_merge()` to combine nested dictionaries
    - Environment variables use prefix `LEVELUP_` with nested delimiter `__`
    - Example: `LEVELUP_PIPELINE__REQUIRE_CHECKPOINTS=false`
- **CLI flag overrides** in `src/levelup/cli/app.py`:
    - `--no-checkpoints` flag sets `pipeline.require_checkpoints` to False
    - Overrides passed as dict to `load_settings(overrides=...)`

### Checkpoint System Architecture

- **Checkpoints occur after**: requirements, test_writing, security, and review steps
- **Two checkpoint modes**:
    1. **Terminal mode** (default): `run_checkpoint()` in `checkpoint.py` → prompts via terminal
    2. **DB mode** (headless/GUI): `_wait_for_checkpoint_decision()` in orchestrator → polls DB for decision
- **Checkpoint logic in orchestrator.py** (`_execute_steps()`, lines 456-494):
    - Checks `settings.pipeline.require_checkpoints` before running checkpoint
    - If `require_checkpoints` is False, checkpoint is skipped entirely
    - If True and `_use_db_checkpoints` is True, waits for GUI decision via DB
    - If True and `_use_db_checkpoints` is False, prompts user in terminal
- **Checkpoint decisions**: approve, revise, instruct, reject
- **Journal logging**: `journal.log_checkpoint(step_name, decision, feedback)`
- **Display data**: `build_checkpoint_display_data()` serializes checkpoint content for DB or display

### Ticket System Architecture

- **Markdown-based tickets** stored in `levelup/tickets.md` (configurable via `project.tickets_file`)
- **Ticket model** in `src/levelup/core/tickets.py`:
    - `Ticket` class: `number`, `title`, `description`, `status` (pending/in progress/done/merged)
    - Status tags in markdown: `## [status] Title` (pending tickets have no tag)
    - **No metadata support currently** - only 4 fields (number, title, description, status)
- **Parsing functions**:
    - `parse_tickets(text)` - parses markdown into Ticket objects
    - `read_tickets(project_path, filename)` - reads from file
    - `get_next_ticket()` - returns first pending ticket
- **Modification functions**:
    - `set_ticket_status()` - updates status tag in-place
    - `update_ticket()` - updates title and/or description
    - `add_ticket()` - appends new ticket
    - `delete_ticket()` - removes ticket
- **Format**: Uses `## ` headings (H2), status in `[status]` tag, description follows heading
- **Code block handling**: Parser tracks fenced code blocks (```) to avoid false heading matches
- **CLI integration**:
    - Every run creates or links to a ticket
    - `--ticket N` runs specific ticket, `--ticket-next` auto-picks next pending
    - Auto-transitions: pending→in progress on run start, in progress→done on completion
    - One active run per ticket enforced via `StateManager.has_active_run_for_ticket()`
- **State DB**: `runs.ticket_number` column links runs to tickets (added in DB v4)

### Git Worktree Workflow

- LevelUp uses git worktrees for concurrent pipeline execution
- Each pipeline run creates:
    - A new branch (e.g., `levelup/{run_id}`) in the main repository
    - A worktree directory at `~/.levelup/worktrees/{run_id}`
- On pipeline completion:
    - The worktree directory is removed (`_cleanup_worktree()` at line 826-836)
    - The branch PERSISTS in the main repository for user to review/merge
    - User is responsible for manually merging or pushing the branch
- Orchestrator prints completion message (lines 262-269) showing:
    - Branch name
    - Suggested git commands for user to manually checkout/merge
    - **ISSUE**: Current message shows incorrect workflow: `git checkout {branch}` then `git merge {branch}` which would try to merge a branch into itself
    - **CORRECT**: Should guide user to either (1) push to remote, OR (2) switch to main branch first before merging
- Worktree cleanup happens for all statuses EXCEPT `PAUSED` (line 272-273)
- The `_cleanup_worktree()` method:
    - Only removes the worktree directory using `git worktree remove --force`
    - Does NOT delete branches (branches persist for user review)
    - Uses `--force` flag to handle Windows permission errors gracefully
    - Is called from both `run()` and `resume()` methods on completion

### Pipeline Orchestrator Structure

- `Orchestrator.run()` method (lines 195-276):
    - Main entry point for pipeline execution
    - Creates worktree and branch if `create_git_branch` is enabled
    - Executes all pipeline steps
    - On successful completion (status == COMPLETED):
        - Commits the journal
        - Prints branch completion message (lines 265-269) - **THIS IS THE PROBLEM**
        - Cleans up worktree (but preserves branch)
- `Orchestrator.resume()` method (lines 278-378):
    - Resumes a previously failed/aborted/paused run
    - Can recreate worktree from existing branch
    - On successful completion:
        - Commits the journal
        - Does NOT print branch completion message (intentional - branch already exists)
        - Cleans up worktree (but preserves branch)
- Both methods share `_cleanup_worktree()` for cleanup

### Rich Console Output

- Uses `rich.console.Console` for terminal output formatting
- Console instance stored in `self._console` in Orchestrator
- Supports rich text formatting: `[bold]`, `[yellow]`, etc.
- Multi-line strings printed with `self._console.print()`

### GUI Architecture

- **Framework**: PyQt6
- **Entry point**: `src/levelup/gui/app.py` - launches QApplication and MainWindow
- **Main window**: `src/levelup/gui/main_window.py` - dashboard with run table and ticket sidebar
- **Theming**:
    - Theme manager: `src/levelup/gui/theme_manager.py` - handles theme preferences and system detection
    - Two themes available: `DARK_THEME` and `LIGHT_THEME` defined in `src/levelup/gui/styles.py`
    - Theme preferences: "light", "dark", or "system" (default: "system")
    - System theme detection via `darkdetect` library (already in dependencies)
        - Applied globally via `app.setStyleSheet()` in `app.py`
        - Terminal emulator has its own color scheme class: `CatppuccinMochaColors` in `terminal_emulator.py`
        - Some widgets use inline `setStyleSheet()` calls for specific styling (e.g., ticket_detail.py, ticket_sidebar.py)
    - **Theme switcher UI**: Currently a QComboBox dropdown in main_window.py toolbar (lines 82-101) with label "Theme:"
- **Key widgets**:
    - `checkpoint_dialog.py` - Modal dialog for approving/revising/rejecting pipeline steps
    - `terminal_emulator.py` - Full VT100 terminal emulator with pyte + pywinpty/ptyprocess
    - `ticket_detail.py` - Ticket editing and run terminal view
    - `ticket_sidebar.py` - Ticket list navigation with icon button ("+" button for adding tickets)
    - `run_terminal.py` - Terminal wrapper for running levelup commands
- **Key widgets**:
    - `checkpoint_dialog.py` - Modal dialog for approving/revising/rejecting pipeline steps
    - `terminal_emulator.py` - Full VT100 terminal emulator with pyte + pywinpty/ptyprocess
    - `ticket_detail.py` - Ticket editing and run terminal view
    - `ticket_sidebar.py` - Ticket list navigation (lines 45-72 implement set_tickets() method)
    - `run_terminal.py` - Terminal wrapper for running levelup commands
- **Theming**:
    - Current theme: Catppuccin Mocha (dark theme) defined in `src/levelup/gui/styles.py`
    - Applied globally via `app.setStyleSheet(DARK_THEME)` in `app.py`
    - Some widgets use inline `setStyleSheet()` calls for specific styling
- **Resources**: `resources.py` contains status colors, labels, and icons

### Ticket-Run Relationship

- **Tickets**: Defined in `src/levelup/core/tickets.py` with statuses: `pending`, `in progress`, `done`, `merged`
- **Runs**: Defined in `src/levelup/state/models.py` with statuses: `pending`, `running`, `waiting_for_input`, `paused`, `completed`, `failed`, `aborted`
- **Link**: `RunRecord.ticket_number` field links runs to tickets (one-to-many relationship)
- **Sidebar Display**: `TicketSidebarWidget` currently colors tickets based on ticket status only, not run status
    - Line 62 in `ticket_sidebar.py`: calls `get_ticket_status_color(ticket.status.value, theme=self._current_theme)`
    - Color is applied to QListWidgetItem via `setForeground(QColor(color))` on line 63
- **Main Window Refresh**: `MainWindow._refresh()` loads both runs (`_runs`) and tickets (`_cached_tickets`) but doesn't pass run status to sidebar
    - Line 174 in `main_window.py`: loads runs via `self._state_manager.list_runs()`
    - Line 189-190: loads tickets and calls `self._sidebar.set_tickets(tickets)`
    - No run status information is passed to sidebar

### Color Scheme (Catppuccin Mocha)

- **Dark theme colors in `resources.py`**:
    - Ticket "in progress": `#E6A817` (yellow-orange)
    - Run "running": `#4A90D9` (blue)
    - Run "waiting_for_input": `#E6A817` (yellow-orange, same as ticket in progress)
- **Light theme colors**:
    - Ticket "in progress": `#F39C12` (orange)
    - Run "running": `#3498DB` (blue)
    - Run "waiting_for_input": `#F39C12` (orange)

### Resources Module Color Functions

- `get_ticket_status_color(status, theme="dark")` - Returns theme-aware color for ticket status (lines 97-110)
    - Accepts ticket status string ("pending", "in progress", "done", "merged")
    - Returns hex color from `TICKET_STATUS_COLORS` (dark) or `_LIGHT_TICKET_STATUS_COLORS` (light)
    - Currently has no awareness of run status
- `get_status_color(status, theme="dark")` - Returns theme-aware color for run status (lines 50-63)
    - Accepts run status string ("running", "waiting_for_input", etc.)
    - Returns hex color from `STATUS_COLORS` (dark) or `_LIGHT_STATUS_COLORS` (light)

### State Manager Query Methods

- `list_runs(status_filter=None, limit=50)` - Returns list of RunRecord objects (lines 141-159)
- `get_run_for_ticket(project_path, ticket_number)` - Returns most recent run for a ticket (lines 171-187)
- `has_active_run_for_ticket(project_path, ticket_number)` - Returns non-completed run for ticket (lines 189+)
- **Table structure**:
    - `_update_table()` (lines 193-208) populates table from `self._runs` list
    - Column data extracted from `RunRecord` fields
    - Status column uses color from `STATUS_COLORS` dict
- **Detail view**:
    - `_view_details()` (lines 448-465) shows message box with run info
    - Currently displays: run_id, task_title, task_description, project_path, status, current_step, language, framework, test_runner, error_message, started_at, updated_at, pid
    - Does NOT display: total_cost_usd, token counts

### Configuration

- Uses Pydantic settings with environment variable support
- Settings classes in `src/levelup/config/settings.py`:
    - `LLMSettings` - LLM backend configuration
    - `ProjectSettings` - Project-specific settings
    - `PipelineSettings` - Pipeline behavior settings
    - `GUISettings` - GUI configuration including theme preference (default: "system")
        - `LevelUpSettings` - Root settings class with nested models
- Configuration loading in `src/levelup/config/loader.py`:
    - Searches for config files: `levelup.yaml`, `levelup.yml`, `.levelup.yaml`, `.levelup.yml`
    - Layered config: defaults → file → env vars → overrides
- GUI theme preference stored in config under `gui.theme` key

### State Management

- **SQLite database** at `~/.levelup/state.db` (override via `--db-path`)
- **StateManager** in `src/levelup/state/manager.py`:
    - `register_run(ctx)` - creates run record
    - `update_run(ctx)` - updates status, step, context JSON
    - `get_run(run_id)` - retrieves run
    - `has_active_run_for_ticket(project_path, ticket_number)` - checks for active run
    - `create_checkpoint_request()` - creates checkpoint request for GUI
    - `get_checkpoint_decision()` - polls for checkpoint decision
- **Models** in `src/levelup/state/models.py`:
    - `RunRecord` - represents a run (includes `ticket_number` field)
    - `CheckpointRequestRecord` - represents a checkpoint awaiting decision
- **Database schema** (`src/levelup/state/db.py`):
    - `runs` table with `ticket_number` column
    - `checkpoint_requests` table for headless/GUI checkpoint coordination
    - Current version: v4 (added ticket_number and index)

### Journal System

- **RunJournal** in `src/levelup/core/journal.py`:
    - Creates markdown log in `levelup/` directory
    - Filename format: `{date}-{ticket}-{slug}.md`
    - Logs header, steps, checkpoints, outcome
- **Checkpoint logging**: `log_checkpoint(step_name, decision, feedback)`
    - Records decision (approve/revise/reject) and optional feedback
    - Appends to journal as `### Checkpoint: {step_name}` section

### Testing Patterns

- **Unit tests** in `tests/unit/`
- **Integration tests** in `tests/integration/`
- Uses pytest with standard assertions
- Path normalization needed on Windows: `.replace("\\", "/")` in assertions
- Test runner: `.venv/Scripts/python.exe -m pytest tests/ -v`
- Mocking with `unittest.mock.patch`
- Typer CLI testing with `typer.testing.CliRunner`

### Styling Patterns

- Global stylesheet applied to QApplication in `app.py`
- Widget-specific styles use `setObjectName()` for ID selectors (e.g., `#saveBtn`, `#approveBtn`)
- Some widgets have inline `setStyleSheet()` calls for custom colors
- Status colors for runs and tickets defined in `resources.py`
- Terminal emulator uses custom color scheme class with QColor objects
- Icon button pattern: Small square buttons with text symbols (e.g., "+" button in ticket sidebar)
    - Styled via `#objectName` selectors in styles.py
    - Example: `#addTicketBtn` - 28x28px square button with centered text
    - Pattern for icon buttons: QPushButton with objectName, fixed size (28x28px), centered symbol, no min-width override, appropriate hover states

### System Theme Detection

- PyQt6 doesn't provide native cross-platform dark mode detection API
- Currently using `darkdetect` library (cross-platform, supports Windows/macOS/Linux)
- darkdetect provides: `theme()` returns "Dark"/"Light", `isDark()`, `isLight()`, and `listener()` for watching changes
- Alternative: PyQt6's `QStyleHints.colorScheme()` (Qt 6.5+) but less reliable across platforms
- System theme detection works correctly in `app.py` on startup through `get_system_theme()` function
- Default behavior: when `gui.theme` is "system" (default), `get_current_theme()` calls `get_system_theme()` which returns "light" or "dark"
- Fallback: if darkdetect unavailable or fails, defaults to "dark" theme

### Testing Patterns

- Unit tests in `tests/unit/`
- Integration tests in `tests/integration/`
- Integration tests in `tests/integration/`
- Theme-related tests: `test_theme_switcher_ui.py`, `test_theme_settings.py`, `test_theme_manager.py`, `test_app_theme_integration.py`, `test_theme_switching_integration.py`
- Tests use pytest with standard assertions
- Mocking patterns: Use `unittest.mock.MagicMock` and `@patch` decorator for agent/LLM mocking
- Path normalization needed on Windows: `.replace("\\", "/")` in assertions
- Existing test patterns:
    - `test_gui_tickets.py` - Tests ticket status colors and icons without Qt dependencies
    - `test_theme_aware_resources.py` - Tests theme-aware color functions for both light and dark themes
    - Tests verify semantic colors (green for success, red for error) preserved across themes
    - Tests check color readability (luminance) for both light and dark backgrounds
- Theme switcher tests expect either QComboBox or QPushButton (flexible)
- Tests verify:
    - Theme control exists and is visible
    - Has tooltip
    - Theme changes apply immediately
    - Theme preference is saved
    - All three theme options (light/dark/system) are available
    - Current theme is indicated
- Comprehensive usage tracking tests in `tests/unit/test_cost_tracking.py`
    - Tests for `AgentResult` defaults and values
    - Tests for `ToolLoopResult` token accumulation
    - Tests for backend integration (ClaudeCodeBackend, AnthropicSDKBackend)
    - Tests for `StepUsage` model serialization
    - Tests for `PipelineContext` step_usage persistence
    - Tests for DB migration v2 (adding total_cost_usd column)
    - Tests for StateManager cost persistence
    - Tests for Journal cost tracking in logs
- DB migration testing pattern:
    - Create database at old version
    - Run `init_db()` to apply migrations
    - Verify schema version updated
    - Verify new columns exist via `PRAGMA table_info()`
- Agent tests: Mock `backend.run_agent()` to return `AgentResult` objects
- Pipeline tests: Mock individual agents and detection steps to test orchestration flow
- Test orchestrator mocking:
    - Mock `_run_detection`, `_run_agent_with_retry`, `shutil.which`, `subprocess.run`
    - Use `side_effect` to control agent behavior (e.g., lambda name, ctx: ctx)
    - Verify call counts to check pipeline execution
- Tests for git worktree behavior in `tests/unit/test_concurrent_worktrees.py`:
    - Verify branches persist after cleanup (lines 226-230)
    - Test concurrent worktree creation and cleanup
    - Verify worktree directories are removed but branches remain
- Tests for branch naming in `tests/unit/test_branch_naming_orchestrator.py`:
    - Test branch creation with custom conventions
    - Test placeholder substitution
    - Test detection loading/writing branch naming

### Key Dependencies

- PyQt6 for GUI (installed via `gui` or `dev` optional dependencies)
- Pydantic for configuration
- pyte for terminal emulation
- pywinpty (Windows) / ptyprocess (Unix) for PTY support
- darkdetect for system theme detection (already included in optional dependencies)

### Theme Switcher Implementation Details

- Current implementation: QComboBox dropdown with "Light", "Dark", "Match System" options
- Location: main_window.py lines 82-101 (toolbar section)
- Method `_on_theme_changed()` handles theme selection changes
- Theme cycling for button implementation: system → light → dark → system
- Theme symbols for button: '◐' for system, '☀' for light, '☾' for dark
- Tooltip pattern: "Theme: Match System", "Theme: Light", "Theme: Dark"
- darkdetect for system theme detection (already installed)
