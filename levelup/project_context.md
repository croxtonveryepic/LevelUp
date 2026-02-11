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

### GUI Ticket Sidebar Color System

- **Ticket statuses**: pending, in progress, done, merged (defined in `core/tickets.py`)
- **Run statuses**: pending, running, waiting_for_input, paused, completed, failed, aborted (defined in `core/context.py`)
- **Color logic** (`gui/resources.py`):
    - `get_ticket_status_color(status, theme, run_status)` accepts optional `run_status` parameter
    - For "in progress" tickets with active runs (running/waiting_for_input), uses run status color
    - Blue (#4A90D9 dark, #3498DB light) for "running" status
    - Yellow-orange (#E6A817 dark, #F39C12 light) for "waiting_for_input" status
    - Other ticket statuses ignore run status and use ticket status color
- **Sidebar implementation** (`gui/ticket_sidebar.py`):
    - `set_tickets()` accepts optional `run_status_map: dict[int, str]` parameter
    - Stores run status map in `_run_status_map` instance variable
    - Passes run status to `get_ticket_status_color()` when rendering items
    - `update_theme()` preserves run status map when re-rendering
- **Main window integration** (`gui/main_window.py`):
    - `_refresh_tickets()` builds run status map from `self._runs`
    - Only includes "running" and "waiting_for_input" statuses in map
    - Passes run status map to `sidebar.set_tickets()`
- **Comprehensive test coverage** in `tests/unit/test_ticket_sidebar_run_status_colors.py`

### Usage Tracking Architecture

- **Markdown-based tickets** stored in `levelup/tickets.md` (configurable via `project.tickets_file`)
- **Ticket model** in `src/levelup/core/tickets.py`:
    - `Ticket` class: `number`, `title`, `description`, `status` (pending/in progress/done/merged), `metadata` (dict)
    - Status tags in markdown: `## [status] Title` (pending tickets have no tag)
    - **Metadata support**: Optional YAML metadata in HTML comment blocks beneath ticket heading
        - Format: `<!--metadata\nkey: value\n-->`
        - Used for auto_approve flag and can be extended for other fields
        - Parser ignores metadata in code blocks
- **Parsing functions**:
    - `parse_tickets(text)` - parses markdown into Ticket objects, extracts metadata from HTML comments
    - `read_tickets(project_path, filename)` - reads from file
    - `get_next_ticket()` - returns first pending ticket
- **Modification functions**:
    - `set_ticket_status()` - updates status tag in-place, preserves metadata
    - `update_ticket()` - updates title, description, and/or metadata
    - `add_ticket()` - appends new ticket with optional metadata
    - `delete_ticket()` - removes ticket
- **Format**: Uses `## ` headings (H2), status in `[status]` tag, metadata in HTML comment, description follows
- **Code block handling**: Parser tracks fenced code blocks (```) to avoid false heading matches
- **CLI integration**:
    - Every run creates or links to a ticket
    - `--ticket N` runs specific ticket, `--ticket-next` auto-picks next pending
    - Auto-transitions: pending→in progress on run start, in progress→done on completion
    - One active run per ticket enforced via `StateManager.has_active_run_for_ticket()`
    - Ticket marked as "done" in `cli/app.py` run() function after successful completion (lines 194-203)
- **State DB**: `runs.ticket_number` column links runs to tickets (added in DB v4)

### Git Branch Creation and Tracking

- **Branch creation**: Orchestrator creates branches using `_create_git_branch()` method (line ~850 in orchestrator.py)
- **Branch naming**: `_build_branch_name()` method (line 771) builds branch names from convention patterns
    - Supports placeholders: `{run_id}`, `{task_title}`, `{date}`
    - Default: `levelup/{run_id}`
    - Convention stored in `PipelineContext.branch_naming`
- **Branch persistence**: After pipeline completion:
    - Worktree is cleaned up via `_cleanup_worktree()` (branches persist)
    - Branch name printed to console with git commands (lines 288-297, 402-410)
    - Branch exists in main repository for user to merge/push
- **PipelineContext tracking**:
    - `branch_naming` field stores the convention pattern
    - `pre_run_sha` tracks the commit before branch creation
    - `worktree_path` tracks the worktree directory location
- **Completion flow**:
    1. Pipeline completes successfully (status = COMPLETED)
    2. Journal committed to branch
    3. Branch completion message printed to console
    4. Ticket marked as "done" (CLI integration)
    5. Worktree cleaned up, branch persists

### PipelineContext Data Model

- **Core fields**:
    - `run_id`, `started_at`, `task`, `project_path`
    - `language`, `framework`, `test_runner`, `test_command`, `branch_naming`
    - `requirements`, `plan`, `test_files`, `code_files`, `test_results`, `review_findings`
    - `status`, `current_step`, `code_iteration`, `error_message`
    - `step_usage` (dict[str, StepUsage]) - Tracks cost/tokens per step
- **Git tracking fields**:
    - `pre_run_sha` - commit SHA before run started
    - `step_commits` - dict mapping step names to commit SHAs
    - `worktree_path` - path to worktree directory
    - `branch_naming` - branch naming convention pattern
- **TestResult model**: Contains `passed`, `total`, `failures`, `errors`, `output`, `command`
- Context flows through entire pipeline, agents modify and return it

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

### Ticket Completion Flow

- **Location**: `src/levelup/cli/app.py` lines 194-203
- **Trigger**: After `orchestrator.run()` completes successfully
- **Current implementation**:
    ```python
    if ctx.status.value == "completed" and ctx.task.source == "ticket" and ctx.task.source_id:
        from levelup.core.tickets import TicketStatus, set_ticket_status
        try:
            ticket_num = int(ctx.task.source_id.split(":")[1])
            set_ticket_status(path, ticket_num, TicketStatus.DONE, settings.project.tickets_file)
            console.print(f"[green]Ticket #{ticket_num} marked as done.[/green]")
        except (IndexError, ValueError):
            pass
    ```
- **Branch name access**: Can be reconstructed using `orchestrator._build_branch_name(ctx.branch_naming or "levelup/{run_id}", ctx)`
- **Extension point**: This is where branch name should be recorded to ticket metadata

### Testing Patterns

- **Unit tests** in `tests/unit/`
- **Integration tests** in `tests/integration/`
- Uses pytest with standard assertions
- Path normalization needed on Windows: `.replace("\\", "/")` in assertions
- Test runner: `.venv/Scripts/python.exe -m pytest tests/ -v`
- Mocking with `unittest.mock.patch`
- Typer CLI testing with `typer.testing.CliRunner`
- **Ticket metadata tests**: `tests/unit/test_ticket_metadata.py` demonstrates patterns for:
    - Parsing metadata from HTML comment blocks
    - Writing metadata with `add_ticket()` and `update_ticket()`
    - Preserving metadata through status changes and updates
    - Round-trip serialization of metadata
    - Backward compatibility with tickets without metadata
- **CLI test patterns**: Mock `Orchestrator` and `StateManager` classes, verify function calls and file contents
- **Branch naming tests**: `tests/unit/test_branch_naming_orchestrator.py` shows how to test branch name generation

### Key Dependencies

- PyQt6 for GUI (installed via `gui` or `dev` optional dependencies)
- Pydantic for configuration
- pyte for terminal emulation
- pywinpty (Windows) / ptyprocess (Unix) for PTY support
- darkdetect for system theme detection
