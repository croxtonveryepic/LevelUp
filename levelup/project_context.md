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

### Git Worktree Workflow
- LevelUp uses git worktrees for concurrent pipeline execution
- Each pipeline run creates:
  - A new branch (e.g., `levelup/{run_id}`) in the main repository
  - A worktree directory at `~/.levelup/worktrees/{run_id}`
- On pipeline completion:
  - The worktree directory is removed (`_cleanup_worktree()` at line 826-836)
  - The branch PERSISTS in the main repository for user to review/merge
  - User is responsible for manually merging or pushing the branch
- Orchestrator prints completion message (lines 262-269) showing:
  - Branch name
  - Suggested git commands for user to manually checkout/merge
  - **ISSUE**: Current message shows incorrect workflow: `git checkout {branch}` then `git merge {branch}` which would try to merge a branch into itself
  - **CORRECT**: Should guide user to either (1) push to remote, OR (2) switch to main branch first before merging
- Worktree cleanup happens for all statuses EXCEPT `PAUSED` (line 272-273)
- The `_cleanup_worktree()` method:
  - Only removes the worktree directory using `git worktree remove --force`
  - Does NOT delete branches (branches persist for user review)
  - Uses `--force` flag to handle Windows permission errors gracefully
  - Is called from both `run()` and `resume()` methods on completion

### Pipeline Orchestrator Structure
- `Orchestrator.run()` method (lines 195-276):
  - Main entry point for pipeline execution
  - Creates worktree and branch if `create_git_branch` is enabled
  - Executes all pipeline steps
  - On successful completion (status == COMPLETED):
    - Commits the journal
    - Prints branch completion message (lines 265-269) - **THIS IS THE PROBLEM**
    - Cleans up worktree (but preserves branch)
- `Orchestrator.resume()` method (lines 278-378):
  - Resumes a previously failed/aborted/paused run
  - Can recreate worktree from existing branch
  - On successful completion:
    - Commits the journal
    - Does NOT print branch completion message (intentional - branch already exists)
    - Cleans up worktree (but preserves branch)
- Both methods share `_cleanup_worktree()` for cleanup

### Rich Console Output
- Uses `rich.console.Console` for terminal output formatting
- Console instance stored in `self._console` in Orchestrator
- Supports rich text formatting: `[bold]`, `[yellow]`, etc.
- Multi-line strings printed with `self._console.print()`

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
- Tests for git worktree behavior in `tests/unit/test_concurrent_worktrees.py`:
  - Verify branches persist after cleanup (lines 226-230)
  - Test concurrent worktree creation and cleanup
  - Verify worktree directories are removed but branches remain
- Tests for branch naming in `tests/unit/test_branch_naming_orchestrator.py`:
  - Test branch creation with custom conventions
  - Test placeholder substitution
  - Test detection loading/writing branch naming

### Key Dependencies
- PyQt6 for GUI (installed via `gui` or `dev` optional dependencies)
- Pydantic for configuration
- pyte for terminal emulation
- pywinpty (Windows) / ptyprocess (Unix) for PTY support
- GitPython (`git` module) for git operations
- rich for terminal output formatting
- Would need to add: `darkdetect` for system theme detection
