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

### Configuration
- Uses Pydantic settings with environment variable support
- Settings classes in `src/levelup/config/settings.py`:
  - `LLMSettings` - LLM backend configuration
  - `ProjectSettings` - Project-specific settings
  - `PipelineSettings` - Pipeline behavior settings (includes `require_checkpoints: bool = True`)
  - `GUISettings` - GUI theme configuration
  - `LevelUpSettings` - Root settings class with nested models
- Configuration loading in `src/levelup/config/loader.py`:
  - Searches for config files: `levelup.yaml`, `levelup.yml`, `.levelup.yaml`, `.levelup.yml`
  - Layered config: defaults → file → env vars → overrides
  - Uses `_deep_merge()` to combine nested dictionaries
- CLI flag `--no-checkpoints` overrides `pipeline.require_checkpoints` setting

### Checkpoint System
- Checkpoints occur after: requirements, test_writing, security, and review steps
- Logic in `src/levelup/core/checkpoint.py`:
  - `run_checkpoint()` - displays content and gets user decision via terminal
  - `build_checkpoint_display_data()` - extracts checkpoint data as serializable dict
  - `_display_checkpoint_content()` - renders checkpoint content in terminal
- Orchestrator checkpoint handling in `src/levelup/core/orchestrator.py` (lines 456-494):
  - Checks `settings.pipeline.require_checkpoints` before prompting
  - Supports DB checkpoints (headless/GUI mode) via `_wait_for_checkpoint_decision()`
  - Supports terminal checkpoints via `run_checkpoint()`
  - User can approve, revise, instruct, or reject at each checkpoint
- Decisions handled in `get_checkpoint_decision()` in `src/levelup/cli/prompts.py`

### Ticket System
- Markdown-based tickets stored in `levelup/tickets.md` (configurable via `project.tickets_file`)
- Ticket model in `src/levelup/core/tickets.py`:
  - `Ticket` class: number, title, description, status (pending/in progress/done/merged)
  - Status tags in markdown: `## [status] Title` (pending tickets have no tag)
  - Parsing functions: `parse_tickets()`, `read_tickets()`, `get_next_ticket()`
  - Modification functions: `set_ticket_status()`, `update_ticket()`, `delete_ticket()`, `add_ticket()`
- CLI integration in `src/levelup/cli/app.py`:
  - Every run creates or is linked to a ticket
  - `--ticket N` runs specific ticket, `--ticket-next` auto-picks next pending ticket
  - Auto-transitions: pending→in progress on run start, in progress→done on completion
  - One active run per ticket enforced via state manager
- State DB stores `ticket_number` in runs table (added in DB v4)
- Current ticket format has no metadata/options beyond the four fields

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
- GUI tests exist for non-Qt components (e.g., `test_gui_tickets.py` tests color/icon resources)
- Tests use pytest with standard assertions
- Path normalization needed on Windows: `.replace("\\", "/")` in assertions

### Key Dependencies
- PyQt6 for GUI (installed via `gui` or `dev` optional dependencies)
- Pydantic for configuration
- pyte for terminal emulation
- pywinpty (Windows) / ptyprocess (Unix) for PTY support
- Would need to add: `darkdetect` for system theme detection
