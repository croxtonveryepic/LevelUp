# Project Context

- **Language:** python
- **Framework:** none
- **Test runner:** pytest
- **Test command:** pytest
- **Branch naming:** levelup/{task_title}
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

### Agent Architecture

- **Base Class**: `BaseAgent` (abstract) in `agents/base.py`
    - Constructor: `__init__(backend: Backend, project_path: Path)`
    - Abstract methods: `get_system_prompt()`, `get_allowed_tools()`, `run()`
    - Returns: `tuple[PipelineContext, AgentResult]`
- **Existing Agents**:
    - `RequirementsAgent` - Analyzes task and writes requirements
    - `PlanningAgent` - Creates implementation plan
    - `TestWriterAgent` - Writes failing tests (TDD red phase)
    - `CodeAgent` - Implements code to pass tests
    - `SecurityAgent` - Scans for vulnerabilities and auto-patches
    - `ReviewAgent` - Final code review
    - `ReconAgent` - Standalone (not BaseAgent), explores codebase
- **Agent Pattern**: System prompt + user prompt + allowed tools → Backend.run_agent() → AgentResult
- **Standalone Agents**: ReconAgent doesn't inherit BaseAgent (no PipelineContext), runs independently
- **Standalone Agent Use Cases**: Agents that don't participate in the main TDD pipeline (e.g., ReconAgent, MergeAgent)

### Backend & Tool System

- **Backend Protocol**: `Backend` in `agents/backend.py`
    - Two implementations: `ClaudeCodeBackend` (subprocess), `AnthropicSDKBackend` (API)
    - Method: `run_agent(system_prompt, user_prompt, allowed_tools, working_directory, ...)`
- **Tool Names** (Claude Code conventions): Read, Write, Edit, Glob, Grep, Bash
- **Sandboxing**: All file tools restricted to project directory

### Git & Branch Management

- **Worktrees**: Pipeline runs create git worktrees at `~/.levelup/worktrees/<run_id>/`
- **Branch Naming**: Stored in `ctx.branch_naming` (e.g., `levelup/{task_title}`)
- **Branch Metadata**: Branch name stored in ticket metadata as `branch_name` after completion
- **Step Commits**: Each pipeline step gets a commit (when `create_git_branch: true`)
- **Pre-run SHA**: Stored in `ctx.pre_run_sha` for rollback support
- **Worktree Cleanup**: Removed after run completes (branch persists in main repo)
- **Merge Operations**: Existing rebase-merge skill uses simple git commands, no conflict resolution
- **Main Repository Operations**: Merge operations should run in the main repository (ctx.project_path), not in worktrees

### GUI Architecture

- **Framework**: PyQt6-based desktop GUI
- **Location**: `src/levelup/gui/`
- **Main Window** (`gui/main_window.py`): Dashboard with runs table and ticket management
- **Theme Manager** (`gui/theme_manager.py`): Handles theme preferences (light/dark/system) and applies stylesheets
- **Terminal Emulator** (`gui/terminal_emulator.py`): VT100 terminal using pyte, supports both `CatppuccinMochaColors` (dark) and `LightTerminalColors` (light) schemes
- **Key Components**:
    - `main_window.py`: Main application window that coordinates GUI components
    - `ticket_sidebar.py`: Displays ticket list with status indicators
    - `ticket_detail.py`: Detail view with ticket form (title, description, auto-approve, status label) and embedded RunTerminalWidget
    - `run_terminal.py`: Wrapper around TerminalEmulatorWidget for running pipeline commands
    - `terminal_emulator.py`: VT100 terminal using pyte library with scrollback support
    - `theme_manager.py`: Handles theme preferences (light/dark/system) and applies stylesheets
    - `resources.py`: Defines status-to-color/icon mappings for both dark and light themes
    - `styles.py`: QSS stylesheets for dark and light themes

### Terminal Emulator Architecture

- **Location**: `src/levelup/gui/terminal_emulator.py`
- **Terminal Backend**: Uses `pyte` library for VT100 terminal emulation with PTY (pseudo-terminal) backend
- **Screen State**:
    - `pyte.HistoryScreen` with 10,000 line scrollback buffer
    - Current buffer: `self._screen.buffer` (visible screen rows)
    - History buffer: `self._screen.history.top` (deque of historical lines)
- **Scrollback System**:
    - `_scroll_offset`: Number of lines scrolled up from bottom (0 = at bottom)
    - `wheelEvent()`: Updates scroll offset (±3 lines per wheel event)
    - `paintEvent()`: Renders composite of history + buffer based on scroll offset
- **Rendering Logic** (`paintEvent()` lines 513-606):
    - When `_scroll_offset > 0`: Top rows come from `screen.history.top`, remaining rows from `screen.buffer`
    - Formula: `history_idx = len(history.top) - scroll_offset + row`
    - Transitions from history to buffer at row = `_scroll_offset`
- **Selection & Copy System**:
    - Mouse events track selection: `_selection_start` and `_selection_end` (col, row tuples)
    - `_get_selected_text()`: Extracts text from selection (lines 761-778)
    - **CURRENT BUG**: `_get_selected_text()` always reads from `screen.buffer[row]`, ignoring scroll offset
    - Should read from same composite view as `paintEvent()` (history + buffer based on offset)
- **Copy Shortcuts**:
    - Ctrl+Shift+C: Copy selection
    - Ctrl+C with selection: Copy selection
    - Ctrl+C without selection: Send interrupt to shell
- **Color Schemes**: `CatppuccinMochaColors` (dark) and `LightTerminalColors` (light)

### Terminal Scrollback Bug

- **Issue**: When terminal is scrolled up (`_scroll_offset > 0`), selecting and copying text copies from wrong location
- **Root Cause**: `_get_selected_text()` method always reads from `self._screen.buffer[row]` regardless of scroll position
- **Expected Behavior**: Should read from history when `row < scroll_offset`, just like `paintEvent()` does
- **Test Documentation**: `tests/unit/test_terminal_scrollback_display.py` line 552 documents expected behavior
- **Impact**: User sees highlighted text from history but clipboard gets text from current buffer at same row position

### Ticket System

- **Location**: `src/levelup/core/tickets.py`
- **Storage**: Markdown-based in `levelup/tickets.md` (configurable via `project.tickets_file`)
- **Format**:
    - Level-2 headings (`##`) represent tickets
    - Description text appears after the heading
    - Optional YAML metadata in HTML comments: `<!--metadata ... -->`
    - Status tags in heading: `[in progress]`, `[done]`, `[merged]`
- **Ticket Model** (`Ticket` class):
    - `number`: int (1-based ordinal position in file)
    - `title`: str (heading text without status tag)
    - `description`: str (body text below heading, currently plain text)
    - `status`: TicketStatus enum
    - `metadata`: dict[str, Any] | None (from YAML block)
- **Ticket Statuses** (TicketStatus enum):
    - `PENDING = "pending"` (default, no status tag in markdown)
    - `IN_PROGRESS = "in progress"` (tagged with `[in progress]`)
    - `DONE = "done"` (tagged with `[done]`)
    - `MERGED = "merged"` (tagged with `[merged]`)
- **Parsing**: `_STATUS_PATTERN` regex matches status tags: `^\[(in progress|done|merged)\]\s*` (case-insensitive)
- **CLI Commands**: `levelup tickets [list|next|start|done|merged|delete]`
- **Run Integration**: Runs link to tickets via `runs.ticket_number` column in SQLite DB
- **Branch Name Storage**: After pipeline completion, branch name stored as `branch_name` in ticket metadata
- **Status Transitions**: CLI automatically transitions pending→in progress on run start, in progress→done on pipeline success
- **Metadata Filtering**: Run options (model, effort, skip_planning) are filtered from ticket metadata by `_filter_run_options()`

### Status Change Flow

- **CLI Status Changes**:
    - `set_ticket_status()` function in `core/tickets.py` is the primary API
    - Used by CLI in `cli/app.py` for transitions: pending → in progress (on run start), in progress → done (on completion)
    - CLI `levelup tickets` command supports manual status changes: `levelup tickets done 5` changes ticket #5 to done
- **GUI Status Changes**:
    - Currently no direct status change UI in the GUI - tickets change status only through lifecycle (starting/completing runs)
    - Ticket detail widget displays status as read-only label with icon and color (lines 79-81 in `ticket_detail.py`)
    - Status label uses `TICKET_STATUS_ICONS` dict and `get_ticket_status_color()` for theme-aware coloring
- **Status Persistence**:
    - Status stored as markdown tag in heading: `## [done] Ticket Title`
    - PENDING status has no tag (bare heading)
    - Other statuses use bracketed tags: `[in progress]`, `[done]`, `[merged]`

### Ticket Detail Widget Structure

- Located at `src/levelup/gui/ticket_detail.py`
- Vertical splitter layout: ticket form (top) | terminal (bottom)
- **Current ticket form fields** (lines 69-98):
    - Title: `QLineEdit` (line 74)
    - **Status label**: QLabel showing icon + status text with theme-aware color (lines 79-81) - READ-ONLY
    - Description: `QPlainTextEdit` - **plain text editor** (line 88)
    - Auto-approve checkbox (line 93)
    - Model combo: Default/Sonnet/Opus (line 105)
    - Effort combo: Default/Low/Medium/High (line 112)
    - Skip planning checkbox (line 118)
- **Form field behavior**:
    - Fields populate from ticket data in `set_ticket()` method (lines 264, 275-280)
    - Status label updated with icon, text, and theme-aware color
    - Changes trigger `_mark_dirty()` to enable Save button
- Form fields currently save to ticket metadata via `_build_save_metadata()` (line 427)
- Fields populate from ticket.metadata when ticket loads via `set_ticket()` (line 303)
- Terminal receives settings via `set_ticket_settings()` call (line 367)
- **Button layout**: Located in form section, includes Delete/Cancel/Save buttons (lines 100-120)
- **Save flow** (lines 416-436):
    - `_on_save()` builds metadata from form via `_build_save_metadata()`
    - Emits `ticket_saved` signal with number, title, description, metadata_json
    - MainWindow's `_on_ticket_saved()` handler calls `update_ticket()` to persist changes
    - After save, `_refresh_tickets()` reloads ticket list and updates detail widget

### Ticket Data Flow

1. **GUI → Storage**:
   - User edits description in `QPlainTextEdit` (line 88 of `ticket_detail.py`)
   - On save, `_on_save()` emits `ticket_saved` signal with plain text (line 431)
   - `MainWindow` handles signal and calls `update_ticket()` in `core/tickets.py`
   - `update_ticket()` writes description as plain text to markdown file (line 377)

2. **Storage → GUI**:
   - `parse_tickets()` reads markdown file and extracts description text (line 67 of `tickets.py`)
   - Description lines accumulated in `description_lines` list (line 75)
   - Joined as plain string and stored in `Ticket.description` (line 82-86)
   - `TicketDetailWidget.set_ticket()` loads description into `QPlainTextEdit` (line 283)

3. **CLI Access**:
   - Agents receive ticket via `Ticket.to_task_input()` (line 42 of `tickets.py`)
   - Converts to `TaskInput` with description as string field (line 48)

### Run Terminal Widget Structure

- Located at `src/levelup/gui/run_terminal.py`
- Header layout: status label + Run/Terminate/Pause/Resume/Forget/Clear buttons
- **Run Options Widgets** (lines 100-115): Model combo, Effort combo, Skip planning checkbox
- Stores run options in instance variables (lines 140-143):
    - `_ticket_model: str | None`
    - `_ticket_effort: str | None`
    - `_ticket_skip_planning: bool`
- `set_ticket_settings()` method (line 176) updates these variables
- `build_run_command()` function (line 31) constructs CLI command with optional flags:
    - `--model {model}` (line 49)
    - `--effort {effort}` (line 51)
    - `--skip-planning` (line 53)
- Run button click triggers `_on_run_clicked()` → `start_run()` → `build_run_command()`

### Adaptive Pipeline Settings Flow

- **Ticket metadata → Run command**:
    1. Ticket form saves metadata (model, effort, skip_planning) to tickets.md YAML block
    2. TicketDetailWidget reads ticket.metadata and calls `terminal.set_ticket_settings()`
    3. RunTerminalWidget stores settings in `_ticket_*` variables
    4. When Run clicked, `build_run_command()` adds CLI flags based on stored values
    5. CLI spawns pipeline with flags: `levelup run --ticket N --model X --effort Y --skip-planning`

- **CLI → Orchestrator**:
    1. CLI `run()` function accepts `--model`, `--effort`, `--skip-planning` flags
    2. Orchestrator reads ticket metadata via `_read_ticket_settings()`
    3. Precedence: CLI flags > ticket metadata > config defaults
    4. Auto-approve handled separately via `_should_auto_approve()` (orchestrator.py line 89)

### Auto-Approve Special Case

- Currently stored in ticket metadata like other settings
- Used by orchestrator to skip checkpoint prompts
- **Not** a run-level setting (applies to all runs of a ticket)
- Should remain as ticket-level metadata, not moved to run options
- **Resolution priority** (orchestrator.py `_should_auto_approve()`, line 86):
    1. Ticket metadata `auto_approve` field (if present)
    2. Project-level config `pipeline.auto_approve` (default: False)
- **Current GUI behavior**:
    - `set_ticket()` (line 286-292): Populates checkbox from ticket metadata, defaults to False if not present
    - `set_create_mode()` (line 253-255): Always sets checkbox to False for new tickets
    - **BUG**: Does not respect project's default `pipeline.auto_approve` setting when ticket has no metadata
- **Config system**:
    - `PipelineSettings.auto_approve` field in `config/settings.py` (line 40), default: False
    - Can be set via `levelup.yaml` under `pipeline.auto_approve`
    - Can be set via environment variable `LEVELUP_PIPELINE__AUTO_APPROVE`
    - Config loaded via `load_settings()` from `config/loader.py`
- **Settings loading in GUI**:
    - `MainWindow.__init__()` loads settings via `load_settings(project_path=project_path)` (main_window.py line 62-67)
    - Settings are used to get `tickets_file` configuration
    - `TicketDetailWidget` does NOT currently load settings - needs to be added
    - `set_project_context()` is the natural place to load settings when project path is set

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
    - Dark theme colors in `TICKET_STATUS_COLORS` dict
    - Light theme colors in `_LIGHT_TICKET_STATUS_COLORS` dict
    - Icons in `TICKET_STATUS_ICONS` dict
    - `get_ticket_status_color(status, theme, run_status)` returns theme-aware color
    - Dark theme pending tickets: `#CDD6F4` (light lavender)
    - Light theme pending tickets: `#2E3440` (dark blue-gray) - WCAG AA compliant
    - Tickets without active runs inherit their status color
    - "In progress" tickets show dynamic colors based on run status:
        - Blue (`#4A90D9` dark, `#3498DB` light) when run is "running"
        - Yellow-orange (`#E6A817` dark, `#F39C12` light) when run is "waiting_for_input"
    - Merged tickets: `#6C7086` (dark gray, dark theme), `#95A5A6` (medium gray, light theme)
- **Current Status Colors**:
    - **Dark theme**: pending `#CDD6F4`, in progress `#E6A817`, done `#2ECC71`, merged `#6C7086`
    - **Light theme**: pending `#2E3440`, in progress `#F39C12`, done `#27AE60`, merged `#95A5A6`
- **Accessibility**: Light mode pending ticket color was updated from `#4C566A` to `#2E3440` to meet WCAG AA contrast requirements (4.5:1 minimum) against white background
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

### Testing Patterns

- Unit tests use pytest with PyQt6 fixtures
- Mock state manager using `MagicMock(spec=StateManager)`
- Mock terminal emulator with `patch("levelup.gui.terminal_emulator.PtyBackend")`
- Test files follow pattern: `test_<component>.py` or `test_<component>_<feature>.py`
- Button state tests verify enabled/disabled states after state transitions
- Metadata tests verify round-trip serialization and preservation of non-form fields
- Integration tests use temporary directories (`tmp_path` fixture) for file operations
- Tests for project settings use `load_settings(project_path=tmp_path)` pattern
- Config files created as `tmp_path / "levelup.yaml"` with YAML content
- Auto-approve tests in `test_gui_ticket_metadata.py` verify checkbox behavior
- Terminal scrollback tests located at `tests/unit/test_terminal_scrollback_display.py` (display logic)
- Terminal rendering tests located at `tests/unit/test_terminal_scrollback_rendering.py` (rendering details)

### Ticket Sidebar Widget Structure

- **Location**: `src/levelup/gui/ticket_sidebar.py`
- **Base Class**: `TicketSidebarWidget(QWidget)` - core sidebar implementation
- **Signals**:
    - `ticket_selected = pyqtSignal(int)` - emits ticket number when selected
    - `create_ticket_clicked = pyqtSignal()` - emits when + button clicked
- **Header Layout**: "Tickets" label + "+" button for creating new tickets
- **List Widget**: `QListWidget` displaying tickets with status icons and colors
- **State Variables**:
    - `_tickets: list[Ticket]` - current ticket list
    - `_current_theme: str` - "light" or "dark"
    - `_run_status_map: dict[int, str]` - maps ticket number to run status
- **Key Methods**:
    - `set_tickets(tickets, run_status_map)` - updates ticket list, preserves selection
    - `update_theme(theme)` - changes theme and re-renders colors
    - `clear_selection()` - deselects any selected item
    - `refresh()` - re-renders with current tickets
- **Selection Preservation**: When `set_tickets()` is called, current selection is remembered by ticket number and restored after re-rendering
- **Alias Class**: `TicketSidebar(TicketSidebarWidget)` - adds auto-loading from file when project_path provided

### MainWindow Stacked Widget Pages

- **Page Management**: `QStackedWidget` at `self._stack` holds multiple pages
- **Current Pages** (indices 0-2):
    - **Index 0**: Runs table (`QTableWidget`) - default view showing all pipeline runs
    - **Index 1**: Ticket detail (`TicketDetailWidget`) - ticket form + terminal
    - **Index 2**: Documentation viewer (`DocsWidget`) - markdown file browser
- **Navigation Pattern**:
    - Each page widget has `back_clicked = pyqtSignal()` signal
    - MainWindow connects to `_on_<page>_back()` slots that call `self._stack.setCurrentIndex(0)` to return to runs table
    - Sidebar selection cleared when navigating back
- **Adding New Pages**:
    - Create widget with back button and `back_clicked` signal
    - Add to stack via `self._stack.addWidget(widget)` - returns new index
    - Connect `back_clicked` signal to handler that sets index back to 0
    - Add navigation method to switch to new page (clear sidebar selection, set index)

### Testing Patterns

- **Test Location**: Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- **PyQt6 Tests**: Use `_can_import_pyqt6()` check and `@pytest.mark.skipif` decorator
- **QApplication**: Tests create QApplication instance via `_ensure_qapp()` helper
- **Mocking**: Use `unittest.mock.patch` for GUI components and state managers
- Unit tests use pytest with PyQt6 fixtures
- Mock state manager using `MagicMock(spec=StateManager)`
- Mock terminal emulator with `patch("levelup.gui.terminal_emulator.PtyBackend")`
- Test files follow pattern: `test_<component>.py` or `test_<component>_<feature>.py`
- Button state tests verify enabled/disabled states after state transitions
- Metadata tests verify round-trip serialization and preservation of non-form fields
- Integration tests use temporary directories (`tmp_path` fixture) for file operations
- Tests for project settings use `load_settings(project_path=tmp_path)` pattern
- Config files created as `tmp_path / "levelup.yaml"` with YAML content
- Auto-approve tests in `test_gui_ticket_metadata.py` verify checkbox behavior
- **Specific Test Files**:
    - `tests/unit/test_ticket_sidebar_run_status_colors.py` - 40+ tests covering color logic
- **Test Runner**: pytest with PyQt6 integration
- **Test Dependencies**: Tests use PyQt6 and are skipped if not available
- **Color Assertion Pattern**: Tests assert exact hex color values (e.g., `assert color == "#CDD6F4"`)
- **Ticket Parsing Tests**: Cover all statuses, case-insensitivity, edge cases
- **GUI Tests**: Verify widget initialization, theme updates, button states, metadata persistence
- **Edge Cases Covered**:
    - Invalid statuses/themes
    - None/empty run status values
    - Theme switching with preserved run status
    - Multiple runs for same ticket
    - Selection preservation during updates

### Key Conventions

- Windows paths: Use `.replace("\\", "/")` in test assertions
- Test classes named `Test*` trigger pytest collection warnings (expected)
- SQLite WAL mode for multi-process access
- Git worktrees for concurrent runs at `~/.levelup/worktrees/<run_id>/`
- Parent widgets pass theme to child widgets during construction
- Theme updates propagate via `update_theme(theme)` method
- Widget signals use PyQt6 `pyqtSignal` for inter-component communication
- Form controls block signals during programmatic updates to avoid triggering dirty state

### Existing Merge Skills

- **rebase-merge** (`.claude/commands/rebase-merge.md`):
    - Takes branch name as argument
    - Rebases branch onto master, merges, deletes branch
    - Aborts on conflicts with error message
- **merge-to-master** (`.claude/commands/merge-to-master.md`):
    - Merges current branch into master
    - No rebase step
    - Creates merge commit with `--no-ff`
- **Note**: Both are CLI skills, not agents. They use simple git commands, no conflict resolution.

### MergeAgent Implementation Requirements

- **Agent Type**: Standalone agent (like ReconAgent) - does not inherit BaseAgent since it doesn't participate in TDD pipeline
- **Execution Context**: Runs in main repository (project_path), not in worktree
- **Input**: Retrieves branch_name from ticket metadata
- **Git Operations Flow**:
    1. Validate branch exists and has branch_name in metadata
    2. `git checkout <branch>` to switch to feature branch
    3. `git rebase master` to rebase onto latest master
    4. If conflicts detected, enter intelligent resolution mode
    5. `git checkout master` after successful rebase
    6. `git merge <branch>` (fast-forward merge)
    7. Optionally `git branch -d <branch>` to clean up
- **Conflict Resolution**:
    - Uses Read tool to examine conflict markers
    - For project_context.md, intelligently merges Codebase Insights sections
    - Uses Edit tool to resolve conflicts and remove markers
    - `git add` resolved files
    - `git rebase --continue` to proceed
    - Handles multiple conflict rounds
- **Error Handling**:
    - Validates branch_name exists in metadata
    - Validates git branch exists
    - Aborts rebase if conflicts cannot be auto-resolved
    - Returns descriptive errors without leaving partial state
- **GUI Integration**:
    - Add "Merge" button to RunTerminalWidget header (alongside Run/Terminate/etc.)
    - Button enabled when: ticket status is "done" AND branch_name exists in metadata AND not currently running
    - Clicking spawns MergeAgent with terminal output displayed
    - On success, calls `set_ticket_status(TicketStatus.MERGED)`
    - Status update triggers ticket sidebar refresh

### Image/Asset Handling

- **Current State**: No existing image handling infrastructure
- **Markdown Storage**: Tickets stored in plain markdown files (`levelup/tickets.md`)
- **Description Field**: Currently plain text only (no images, no rich text)
- **Asset Directory**: Project has one screenshot (`gui-initial.png`) but no dedicated assets folder
- **Potential Storage Locations**:
    - `levelup/assets/` or `levelup/ticket-assets/` - new directory for ticket images
    - Base64 encoding in markdown (standard markdown approach)
    - External file references with relative paths in markdown

### PyQt6 Rich Text Support

- **QTextEdit vs QPlainTextEdit**:
    - `QPlainTextEdit`: Plain text only, no formatting, no images (currently used)
    - `QTextEdit`: Supports rich text HTML, images, formatting
- **Image Handling in QTextEdit**:
    - Images can be embedded via HTML `<img>` tags with local file paths or data URIs
    - `insertFromMimeData()` handles clipboard paste operations
    - `toHtml()` / `setHtml()` for HTML↔widget conversion
    - `toPlainText()` / `setPlainText()` for plain text access
    - `document().addResource()` to manage embedded images
- **Markdown Conversion**:
    - Project uses `mistune>=3.0.0` for markdown→HTML (see `docs_widget.py`)
    - Need bidirectional conversion: HTML (QTextEdit) ↔ Markdown (storage)
    - Markdown image syntax: `![alt text](path/to/image.png)`

### Ticket Deletion and Cleanup Patterns

- **Deletion Flow** (see `main_window.py:_on_ticket_deleted()`):
    1. Clean up associated run and git worktree if exists
    2. Call `delete_ticket()` from `core/tickets.py` to remove from markdown file
    3. Refresh ticket list and navigate back to main view
- **Asset Cleanup**: Currently no asset cleanup logic (will need to add for images)
- **Path Resolution**: Project path passed to widgets via `set_project_context()`
- **File Operations**: All ticket file operations use `Path.read_text()` / `Path.write_text()`

### Markdown Parsing and Serialization

- **Parser**: Custom parser in `tickets.py` (not using mistune for parsing)
- **Description Storage**: Currently stored as plain text string in `Ticket.description`
- **Metadata Storage**: YAML in HTML comments (`<!--metadata ... -->`)
- **Code Block Handling**: Parser tracks fenced code blocks to avoid false ticket detection
- **Line Ending Preservation**: Parser preserves original line endings (CRLF/LF)
- **Update Pattern**: Read entire file, modify relevant sections, write back atomically

### Ticket Sidebar Filtering

- **Filter State**: Sidebar needs to maintain filter state for merged ticket visibility
- **Default Behavior**: Merged tickets hidden by default from main sidebar list
- **Toggle Control**: Checkbox or toggle button in sidebar header to show/hide merged tickets
- **Filter Logic**: Applied in `set_tickets()` method or new filter method
- **Statuses Shown by Default**: pending, in progress, done (merged hidden)
- **Selection Preservation**: If selected ticket is filtered out, selection should be cleared or moved to nearest visible ticket
- **Theme Integration**: Filtered tickets should respect theme colors when shown
- **Run Status Integration**: Filtered tickets should still show correct colors based on run status when visible
