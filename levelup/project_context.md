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

### GUI Architecture

- **Framework**: PyQt6
- **Entry point**: `src/levelup/gui/app.py` - launches QApplication and MainWindow
- **Main window**: `src/levelup/gui/main_window.py` - dashboard with run table and ticket sidebar
- **Theming**:
    - Current theme: Catppuccin Mocha (dark theme) defined in `src/levelup/gui/styles.py`
    - Applied globally via `app.setStyleSheet(DARK_THEME)` in `app.py` (line 25)
    - Terminal emulator has its own color scheme class: `CatppuccinMochaColors` in `terminal_emulator.py`
    - Some widgets use inline `setStyleSheet()` calls for specific styling (e.g., ticket_detail.py, ticket_sidebar.py)
- **Key widgets**:
    - `checkpoint_dialog.py` - Modal dialog for approving/revising/rejecting pipeline steps
    - `terminal_emulator.py` - Full VT100 terminal emulator with pyte + pywinpty/ptyprocess
    - `ticket_detail.py` - Ticket editing and run terminal view
    - `ticket_sidebar.py` - Ticket list navigation
    - `run_terminal.py` - Terminal wrapper for running levelup commands
- **Resources**: `resources.py` contains status colors, labels, and icons
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
    - `LevelUpSettings` - Root settings class with nested models
- Configuration loading in `src/levelup/config/loader.py`:
    - Searches for config files: `levelup.yaml`, `levelup.yml`, `.levelup.yaml`, `.levelup.yml`
    - Layered config: defaults → file → env vars → overrides
- No GUI/theme configuration currently exists in settings

### Styling Patterns

- Global stylesheet applied to QApplication in `app.py`
- Widget-specific styles use `setObjectName()` for ID selectors (e.g., `#saveBtn`, `#approveBtn`)
- Some widgets have inline `setStyleSheet()` calls for custom colors
- Status colors for runs and tickets defined in `resources.py`
- Terminal emulator uses custom color scheme class with QColor objects

### System Theme Detection

- PyQt6 doesn't provide native cross-platform dark mode detection API
- Recommended approach: use `darkdetect` library (cross-platform, supports Windows/macOS/Linux)
- darkdetect provides: `theme()` returns "Dark"/"Light", `isDark()`, `isLight()`, and `listener()` for watching changes
- Alternative: PyQt6's `QStyleHints.colorScheme()` (Qt 6.5+) but less reliable across platforms

### Testing Patterns

- Unit tests in `tests/unit/`
- Integration tests in `tests/integration/`
- Tests use pytest with standard assertions
- Mocking patterns: Use `unittest.mock.MagicMock` and `@patch` decorator for agent/LLM mocking
- Path normalization needed on Windows: `.replace("\\", "/")` in assertions
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

### Key Dependencies

- PyQt6 for GUI (installed via `gui` or `dev` optional dependencies)
- Pydantic for configuration
- pyte for terminal emulation
- pywinpty (Windows) / ptyprocess (Unix) for PTY support
- Would need to add: `darkdetect` for system theme detection
