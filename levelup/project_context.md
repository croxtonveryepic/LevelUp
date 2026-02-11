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
- **Resources**: `resources.py` contains status colors, labels, and icons

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
- GUI tests exist for non-Qt components (e.g., `test_gui_tickets.py` tests color/icon resources)
- Theme-related tests: `test_theme_switcher_ui.py`, `test_theme_settings.py`, `test_theme_manager.py`, `test_app_theme_integration.py`, `test_theme_switching_integration.py`
- Tests use pytest with standard assertions
- Path normalization needed on Windows: `.replace("\\", "/")` in assertions
- Theme switcher tests expect either QComboBox or QPushButton (flexible)
- Tests verify:
  - Theme control exists and is visible
  - Has tooltip
  - Theme changes apply immediately
  - Theme preference is saved
  - All three theme options (light/dark/system) are available
  - Current theme is indicated

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
