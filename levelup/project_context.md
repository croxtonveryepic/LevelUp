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

### Testing Conventions
- Unit tests in `tests/unit/test_resume_rollback.py` cover resume/rollback CLI commands
- State manager tests in `tests/unit/test_state_manager.py` cover CRUD operations including `delete_run()`
- Mocking pattern: Uses `@patch` for `StateManager`, `print_banner`, and CLI interactions
- Typer testing: Uses `typer.testing.CliRunner` for CLI command testing

### Relevant Files for Task
- `src/levelup/cli/app.py`: Contains all CLI commands including `resume()` and `rollback()`
- `src/levelup/cli/prompts.py`: Contains `pick_resumable_run()` for interactive selection
- `src/levelup/state/manager.py`: Contains `StateManager.delete_run()` method (already exists!)
- `tests/unit/test_resume_rollback.py`: Contains tests for resume command patterns
- `tests/unit/test_state_manager.py`: Contains tests for `delete_run()` method
