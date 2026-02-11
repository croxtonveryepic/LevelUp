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

### Run Terminal Button States
- **Run button**: Starts a new pipeline run for the current ticket
- **Resume button**: Resumes a paused/failed/aborted run
- **Pause button**: Requests pipeline pause (enabled only while running)
- **Terminate button**: Kills the running pipeline (enabled only while running)
- **Forget button**: Removes run record from database (enabled when run exists and is not running)
- **Button state management**: Handled by `_set_running_state()` and `_update_button_states()` methods
- **Resumable statuses**: `("failed", "aborted", "paused")` defined in `RESUMABLE_STATUSES` constant
- **State detection**: `_is_resumable()` method checks if last run status is in resumable statuses
- **Run tracking**: `_last_run_id` stores the run ID, populated by `_poll_for_run_id()` and `_wire_existing_run()`

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
- GUI tests exist for non-Qt components (e.g., `test_gui_tickets.py` tests color/icon resources)
- Tests use pytest with standard assertions
- Path normalization needed on Windows: `.replace("\\", "/")` in assertions

### Key Dependencies
- PyQt6 for GUI (installed via `gui` or `dev` optional dependencies)
- Pydantic for configuration
- pyte for terminal emulation
- pywinpty (Windows) / ptyprocess (Unix) for PTY support
- Would need to add: `darkdetect` for system theme detection
