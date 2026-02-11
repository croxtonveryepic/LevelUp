# Project Context

- **Language:** python
- **Framework:** none
- **Test runner:** pytest
- **Test command:** pytest
- **Branch naming:** levelup/task-title-in-kebab-case
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

### GUI Architecture

- **Main Window** (`gui/main_window.py`): Dashboard with runs table and ticket management
- **Theme Manager** (`gui/theme_manager.py`): Handles theme preferences (light/dark/system) and applies stylesheets
- **Terminal Emulator** (`gui/terminal_emulator.py`): VT100 terminal using pyte, supports both `CatppuccinMochaColors` (dark) and `LightTerminalColors` (light) schemes
- **Ticket Detail** (`gui/ticket_detail.py`): Detail view with embedded RunTerminalWidget per ticket
- **Run Terminal** (`gui/run_terminal.py`): Wrapper around TerminalEmulatorWidget for running pipeline commands

### Ticket Detail Widget Structure

- Located at `src/levelup/gui/ticket_detail.py`
- Vertical splitter layout: ticket form (top) | terminal (bottom)
- **Current ticket form fields** (lines 92-124):
    - Auto-approve checkbox (line 93)
    - Model combo: Default/Sonnet/Opus (line 105)
    - Effort combo: Default/Low/Medium/High (line 112)
    - Skip planning checkbox (line 118)
- Form fields currently save to ticket metadata via `_build_save_metadata()` (line 427)
- Fields populate from ticket.metadata when ticket loads via `set_ticket()` (line 303)
- Terminal receives settings via `set_ticket_settings()` call (line 367)

### Run Terminal Widget Structure

- Located at `src/levelup/gui/run_terminal.py`
- Header layout: status label + Run/Terminate/Pause/Resume/Forget/Clear buttons
- Stores run options in instance variables (lines 140-143):
    - `_ticket_model: str | None`
    - `_ticket_effort: str | None`
    - `_ticket_skip_planning: bool`
- `set_ticket_settings()` method (line 176) updates these variables
- `build_run_command()` function (line 31) constructs CLI command with optional flags:
    - `--model {model}` (line 49)
    - `--effort {effort}` (line 51)
    - `--skip-planning` (line 53)
- Run button click triggers `_on_run_clicked()` -> `start_run()` -> `build_run_command()`

### Adaptive Pipeline Settings Flow

- **Ticket metadata → Run command**:
    1. Ticket form saves metadata (model, effort, skip_planning) to tickets.md YAML block
    2. TicketDetailWidget reads ticket.metadata and calls `terminal.set_ticket_settings()`
    3. RunTerminalWidget stores settings in `_ticket_*` variables
    4. When Run clicked, `build_run_command()` adds CLI flags based on stored values
    5. CLI spawns pipeline with flags: `levelup run --ticket N --model X --effort Y --skip-planning`

- **CLI → Orchestrator**:
    1. CLI `run()` function accepts `--model`, `--effort`, `--skip-planning` flags (cli/app.py lines 50, 77, 74)
    2. Orchestrator reads ticket metadata via `_read_ticket_settings()` (orchestrator.py line 111)
    3. Precedence: CLI flags > ticket metadata > config defaults
    4. Auto-approve handled separately via `_should_auto_approve()` (orchestrator.py line 89)

### Auto-Approve Special Case

- Currently stored in ticket metadata like other settings
- Used by orchestrator to skip checkpoint prompts
- **Not** a run-level setting (applies to all runs of a ticket)
- Should remain as ticket-level metadata, not moved to run options

### Theme System

- Theme preferences: "light", "dark", "system" (default)
- `get_current_theme()` resolves preference to actual theme ("light" or "dark")
- `apply_theme(app, theme)` applies stylesheet and notifies listeners via `theme_changed()`
- Widgets implement `update_theme(theme)` method to respond to theme changes
- Terminal color schemes are applied via `terminal.set_color_scheme(scheme_class)`
- Application theme is initialized in `gui/app.py` via `apply_theme(app, actual_theme)` before creating MainWindow
- MainWindow initializes with `self._current_theme = get_current_theme()` and passes theme to child widgets

### Terminal Initialization Pattern

- **Delayed initialization**: Terminals do NOT start shell automatically when widget is shown (showEvent)
- Shell is started lazily only when Run or Resume buttons are clicked (via `_ensure_shell()`)
- This prevents spawning unnecessary PTY processes for tickets that are just being viewed
- `RunTerminalWidget` creates `TerminalEmulatorWidget` in `__init__` with default dark color scheme
- Color scheme is changed after creation via `set_color_scheme()` in `TicketDetailWidget._get_or_create_terminal()`

### Button State Management in RunTerminalWidget

- **\_set_running_state(running)**: Updates button states when transitioning between running/not-running
    - Sets `_command_running` flag
    - Enables/disables buttons based on running state and resumable run existence
    - Uses `_is_resumable()` to check if last run can be resumed
- **\_update_button_states()**: Refreshes all button states based on current conditions
    - Checks `_command_running`, `_ticket_number`, `_project_path`, and `_is_resumable()`
    - Ensures consistency with `_set_running_state()`
- **\_is_resumable()**: Returns True if last_run_id exists and status is in ("failed", "aborted", "paused")
- **enable_run(enabled)**: External API for enabling/disabling Run button
    - Respects resumable run state - won't enable if resumable run exists
- **Run button logic**: Enabled only when not running AND no resumable run exists AND has context
- **Resume button logic**: Enabled only when not running AND resumable run exists
- **Forget button logic**: Enabled when not running AND last_run_id exists
    - After Forget, `_last_run_id` is set to None, which unlocks Run button

### Settings Constants (config/settings.py)

- **MODEL_SHORT_NAMES**: Map short names to full model IDs
    - `"sonnet"` → `"claude-sonnet-4-5-20250929"`
    - `"opus"` → `"claude-opus-4-6"`
- **EFFORT_THINKING_BUDGETS**: Map effort levels to thinking token budgets
    - `"low"` → `4096`
    - `"medium"` → `16384`
    - `"high"` → `32768`

### Orchestrator Settings Resolution (core/orchestrator.py)

- **\_read_ticket_settings(ctx)**: Reads model, effort, skip_planning from ticket metadata (line 111)
- **Model resolution** (line 301): CLI flag > ticket metadata > config default
    - CLI flag sets `_cli_model_override=True` to override ticket metadata
    - If no CLI override, resolves from ticket settings using MODEL_SHORT_NAMES
- **Effort resolution** (line 308): CLI > ticket metadata > none
    - Converts to thinking_budget using EFFORT_THINKING_BUDGETS
- **Skip planning resolution** (line 312): CLI > ticket metadata > false
- Settings passed to `_create_backend()` (line 315) with model_override and thinking_budget

### Testing Patterns

- Unit tests use pytest with PyQt6 fixtures
- Mock state manager using `MagicMock(spec=StateManager)`
- Mock terminal emulator with `patch("levelup.gui.terminal_emulator.PtyBackend")`
- Test files follow pattern: `test_<component>.py` or `test_<component>_<feature>.py`
- Button state tests verify enabled/disabled states after state transitions
- Metadata tests verify round-trip serialization and preservation of non-form fields
- Integration tests use temporary directories (`tmp_path` fixture) for file operations

### Key Conventions

- Windows paths: Use `.replace("\\", "/")` in test assertions
- Test classes named `Test*` trigger pytest collection warnings (expected)
- SQLite WAL mode for multi-process access
- Git worktrees for concurrent runs at `~/.levelup/worktrees/<run_id>/`
- Parent widgets pass theme to child widgets during construction
- Theme updates propagate via `update_theme(theme)` method

## Codebase Insights

### GUI Architecture

- **Framework**: PyQt6-based desktop GUI
- **Location**: `src/levelup/gui/`
- **Key Components**:
    - `ticket_sidebar.py`: Displays ticket list with status indicators
    - `resources.py`: Defines status-to-color/icon mappings for both dark and light themes
    - `styles.py`: QSS stylesheets for dark and light themes
    - `main_window.py`: Main application window that coordinates GUI components

### Ticket System

- **Location**: `src/levelup/core/tickets.py`
- **Ticket Statuses**:
    - `PENDING` (default, no status tag in markdown)
    - `IN_PROGRESS` (tagged with `[in progress]`)
    - `DONE` (tagged with `[done]`)
    - `MERGED` (tagged with `[merged]`)
- **Storage**: Markdown-based in `levelup/tickets.md` (configurable)
- **Format**: Level-2 headings (`##`) represent tickets

### Theming System

- **Themes**: Dark (default) and Light
- **Theme Colors**:
    - **Dark Theme**:
        - Background: `#1E1E2E`, `#181825` (list items)
        - Text: `#CDD6F4`
    - **Light Theme**:
        - Background: `#F5F5F5`, `#FFFFFF` (list items)
        - Text: `#2E3440`

### Ticket Sidebar Color Logic

- **Color Mapping** (`src/levelup/gui/resources.py`):
    - Dark theme pending tickets: `#CDD6F4` (light lavender)
    - Light theme pending tickets: `#4C566A` (dark gray-blue) - **NEEDS IMPROVEMENT FOR ACCESSIBILITY**
    - Tickets without active runs inherit their status color
    - "In progress" tickets can show dynamic colors based on run status:
        - Blue (`#4A90D9` dark, `#3498DB` light) when run is "running"
        - Yellow-orange (`#E6A817` dark, `#F39C12` light) when run is "waiting_for_input"
- **Current Issue**: In light mode, pending tickets use `#4C566A` (medium gray) on `#FFFFFF` (white) background, which provides insufficient contrast for WCAG AA compliance (requires 4.5:1 minimum for normal text)
- **Color Function**: `get_ticket_status_color()` in `resources.py` accepts three parameters:
    - `status`: Ticket status string ("pending", "in progress", "done", "merged")
    - `theme`: Theme mode ("light" or "dark")
    - `run_status`: Optional run status for dynamic coloring ("running", "waiting_for_input", etc.)
- **Theme-aware color selection**:
    - Function uses `_LIGHT_TICKET_STATUS_COLORS` dict for light theme
    - Function uses `TICKET_STATUS_COLORS` dict for dark theme
    - Returns default colors for unknown statuses
- **Run Status Integration** (`main_window.py`):
    - `MainWindow._refresh_tickets()` creates run_status_map from active runs
    - Only includes runs with status "running" or "waiting_for_input"
    - Passes run_status_map to `TicketSidebarWidget.set_tickets()`
    - Sidebar stores run_status_map internally for theme switching

### Testing

- **Test Location**: `tests/unit/test_ticket_sidebar_run_status_colors.py`
- **Coverage**: 40+ tests covering color logic for various ticket/run status combinations
- **Test Runner**: pytest with PyQt6 integration
- **Test Dependencies**: Tests use PyQt6 and are skipped if not available
- **Color Assertion Pattern**: Tests assert exact hex color values (e.g., `assert color == "#CDD6F4"`)
- **Theme Testing**: Tests verify color behavior in both light and dark themes
- **Edge Cases Covered**:
    - Invalid statuses/themes
    - None/empty run status values
    - Theme switching with preserved run status
    - Multiple runs for same ticket
    - Selection preservation during updates
