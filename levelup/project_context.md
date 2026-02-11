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
  - `ticket_detail.py` - Ticket editing and run terminal view (manages per-ticket terminal instances)
  - `ticket_sidebar.py` - Ticket list navigation
  - `run_terminal.py` - Terminal wrapper for running levelup commands
- **Resources**: `resources.py` contains status colors, labels, and icons

### Terminal Initialization Flow (Current Behavior - Being Fixed)
- **When a ticket is selected**: `TicketDetailWidget.set_ticket()` is called (line 242 in ticket_detail.py)
- **Terminal creation**: `_show_terminal()` → `_get_or_create_terminal()` creates a `RunTerminalWidget` for that ticket
- **Widget visibility**: When the terminal widget becomes visible, PyQt6 fires the `showEvent()`
- **Shell initialization (CURRENT PROBLEM)**: `RunTerminalWidget.showEvent()` (line 198) calls `_ensure_shell()` (line 200)
- **PTY starts immediately (UNWANTED)**: `_ensure_shell()` calls `self._terminal.start_shell()` which spawns a PTY/shell process
- **Problem**: The shell starts as soon as the ticket is selected/viewed, NOT when the Run button is clicked

### Terminal Initialization Flow (Target Behavior - Delayed Init)
- **Shell should NOT start** when `RunTerminalWidget.showEvent()` is triggered by ticket selection
- **Shell SHOULD start** when user clicks the "Run" button (inside `start_run()` method, line 160)
- **Shell SHOULD start** when user clicks the "Resume" button (inside `_on_resume_clicked()` method, line 311)
- **Implementation approach**: Remove `_ensure_shell()` call from `showEvent()`, keep it in `start_run()` and `_on_resume_clicked()`
- **Benefit**: Avoids spawning unnecessary PTY processes for tickets that are just being viewed, not run

### RunTerminalWidget Lifecycle
- **Widget creation**: Created per-ticket by `TicketDetailWidget._get_or_create_terminal()` (line 135)
- **Reusability**: Same terminal widget is reused across multiple runs for the same ticket
- **State tracking**:
  - `_shell_started` flag (line 70) tracks whether PTY has been initialized
  - `_command_running` flag (line 69) tracks whether a command is actively executing
- **Shell initialization**: `_ensure_shell()` (line 202) is idempotent - only starts shell once
- **Shell cleanup**: `close_shell()` called when terminal widget is deleted (line 164 in ticket_detail.py)

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
- Terminal-specific tests in `tests/unit/test_ticket_detail_terminals.py` verify per-ticket terminal isolation
- Tests use pytest with standard assertions
- Path normalization needed on Windows: `.replace("\\", "/")` in assertions
- PyQt6 tests use `@pytest.mark.skipif(not _can_import_pyqt6())` decorator to skip when PyQt6 unavailable
- GUI widget tests mock the `PtyBackend` to avoid spawning real PTY processes

### Key Dependencies
- PyQt6 for GUI (installed via `gui` or `dev` optional dependencies)
- Pydantic for configuration
- pyte for terminal emulation
- pywinpty (Windows) / ptyprocess (Unix) for PTY support
- Would need to add: `darkdetect` for system theme detection
