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

### GUI Architecture
- **Framework**: PyQt6
- **Entry point**: `src/levelup/gui/app.py` - launches QApplication and MainWindow
- **Main window**: `src/levelup/gui/main_window.py` - dashboard with run table and ticket sidebar
- **Key widgets**:
  - `checkpoint_dialog.py` - Modal dialog for approving/revising/rejecting pipeline steps
  - `terminal_emulator.py` - Full VT100 terminal emulator with pyte + pywinpty/ptyprocess
  - `ticket_detail.py` - Ticket editing and run terminal view
  - `ticket_sidebar.py` - Ticket list navigation
  - `run_terminal.py` - Terminal wrapper for running levelup commands
- **Theming**:
  - Current theme: Catppuccin Mocha (dark theme) defined in `src/levelup/gui/styles.py`
  - Applied globally via `app.setStyleSheet(DARK_THEME)` in `app.py`
  - Some widgets use inline `setStyleSheet()` calls for specific styling
- **Resources**: `resources.py` contains status colors, labels, and icons

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

### Key Dependencies
- PyQt6 for GUI (installed via `gui` or `dev` optional dependencies)
- Pydantic for configuration
- pyte for terminal emulation
- pywinpty (Windows) / ptyprocess (Unix) for PTY support
- typer for CLI framework
- rich for terminal output formatting
- GitPython for git operations

### Auto-Approve Implementation Considerations
Based on the codebase analysis:
1. **Settings**: Add `auto_approve: bool = False` to `PipelineSettings` in `settings.py`
2. **Environment variable**: Will automatically work via Pydantic: `LEVELUP_PIPELINE__AUTO_APPROVE=true`
3. **CLI flag**: Add `--auto-approve` flag to `run` command in `cli/app.py`, add to overrides dict
4. **Ticket metadata**: Need to extend ticket parsing to support metadata (recommend YAML frontmatter or HTML comment)
5. **Orchestrator logic**: Modify checkpoint section in `_execute_steps()` (lines 456-494) to check auto-approve
6. **Priority order**: ticket metadata → project setting → normal checkpoint flow
7. **Journal logging**: Use existing `log_checkpoint()` with decision="auto-approved"
8. **DB checkpoint skip**: When auto-approved, skip `_wait_for_checkpoint_decision()` and `run_checkpoint()` entirely
9. **GUI integration**: Add checkbox to `TicketDetailWidget` for per-ticket auto-approve
10. **CLI command**: Add `levelup tickets set-metadata <N>` subcommand for metadata editing
11. **Backward compatibility**: Tickets without metadata should continue to work (metadata defaults to None)
