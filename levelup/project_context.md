# Project Context

- **Language:** python
- **Framework:** none
- **Test runner:** pytest
- **Test command:** pytest

## Codebase Insights

### Project Structure
- **CLI layer**: `src/levelup/cli/` - Contains CLI application (`app.py`), prompts (`prompts.py`), and display utilities
- **State management**: `src/levelup/state/` - SQLite-based state store with `StateManager`, `RunRecord` models, and DB schema
- **Core logic**: `src/levelup/core/` - Contains orchestrator, context, pipeline steps, and checkpoint handling
- **Agents**: `src/levelup/agents/` - AI agent implementations and backend protocols
- **GUI**: `src/levelup/gui/` - PyQt6-based dashboard for monitoring and controlling runs
- **Tests**: `tests/unit/` and `tests/integration/` - Comprehensive test coverage with 507+ passing tests

### Key Architectural Patterns
- **Typer-based CLI**: All commands are defined as `@app.command()` decorated functions in `src/levelup/cli/app.py`
- **State persistence**: SQLite database at `~/.levelup/state.db` (configurable via `--db-path`) stores run records
- **StateManager CRUD**: Provides methods like `register_run()`, `update_run()`, `get_run()`, `list_runs()`, `delete_run()`
- **Interactive prompts**: Uses `prompt_toolkit` for interactive CLI experiences (task input, checkpoints, run selection)
- **Resume pattern**: The `resume` command supports both explicit ID (`levelup resume <run-id>`) and interactive picker mode (`levelup resume`)
- **GUI cleanup**: GUI has a "Clean Up" button that removes completed/failed/aborted runs using `StateManager.delete_run()`

### CLI Command Patterns
- **Dual-mode commands**: Commands like `resume` support both explicit arguments and interactive selection when argument is omitted
- **Interactive pickers**: The `pick_resumable_run()` function in `prompts.py` displays a Rich table and prompts for selection by number or 'q' to quit
- **Confirmation dialogs**: Use `confirm_action()` from `prompts.py` for yes/no confirmations (e.g., GUI install)
- **Rich output**: Commands use Rich library for formatted tables, colored status badges, and styled console output
- **Error handling**: Use `print_error()` from `display.py` and `raise typer.Exit(1)` for error states
- **Banner display**: Most interactive commands call `print_banner()` at the start
- **StateManager kwargs**: Commands accept `--db-path` option and pass as `mgr_kwargs = {"db_path": db_path}` to StateManager
- **Run filtering**: Resume command filters runs by status: `r.status in ("failed", "aborted") and r.context_json`

### Testing Conventions
- Unit tests in `tests/unit/test_resume_rollback.py` cover resume/rollback CLI commands
- State manager tests in `tests/unit/test_state_manager.py` cover CRUD operations including `delete_run()`
- Mocking pattern: Uses `@patch` for `StateManager`, `print_banner`, and CLI interactions
- Typer testing: Uses `typer.testing.CliRunner` for CLI command testing
- Test structure: Organize tests by command/feature in classes like `TestCLIResume`, `TestCLIRollback`
- Interactive prompt testing: Mock `prompt_toolkit.pt_prompt` with return values or side effects for input sequences
- Assertions: Check `result.exit_code` and `result.output` for CLI tests
- Path handling: On Windows, use `.replace("\\", "/")` in test assertions involving paths

### StateManager API
- `delete_run(run_id: str)`: Deletes a run and its checkpoint requests (already exists!)
- `list_runs(status_filter: str | None = None, limit: int = 50)`: Returns list of RunRecord objects
- `get_run(run_id: str)`: Returns single RunRecord or None
- `mark_dead_runs()`: Cleans up dead processes automatically

### Relevant Files for Forget Command Task
- `src/levelup/cli/app.py`: Contains all CLI commands including `resume()` and `rollback()`
- `src/levelup/cli/prompts.py`: Contains `pick_resumable_run()` for interactive selection (can be reused/adapted)
- `src/levelup/state/manager.py`: Contains `StateManager.delete_run()` method (already exists!)
- `tests/unit/test_resume_rollback.py`: Contains tests for resume command patterns (template for forget tests)
- `tests/unit/test_state_manager.py`: Contains tests for `delete_run()` method
- `README.md`: Documentation for all CLI commands
