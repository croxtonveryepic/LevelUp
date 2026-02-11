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
  - `ticket_sidebar.py` - Ticket list navigation (lines 45-72 implement set_tickets() method)
  - `run_terminal.py` - Terminal wrapper for running levelup commands
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
- Existing test patterns:
  - `test_gui_tickets.py` - Tests ticket status colors and icons without Qt dependencies
  - `test_theme_aware_resources.py` - Tests theme-aware color functions for both light and dark themes
  - Tests verify semantic colors (green for success, red for error) preserved across themes
  - Tests check color readability (luminance) for both light and dark backgrounds

### Key Dependencies
- PyQt6 for GUI (installed via `gui` or `dev` optional dependencies)
- Pydantic for configuration
- pyte for terminal emulation
- pywinpty (Windows) / ptyprocess (Unix) for PTY support
- darkdetect for system theme detection (already installed)
