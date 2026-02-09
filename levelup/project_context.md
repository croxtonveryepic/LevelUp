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
- **Detection**: `src/levelup/detection/` - Auto-detects project language, framework, and test runner
- **Configuration**: `src/levelup/config/` - Pydantic-based settings (LLM, project, pipeline)
- **GUI**: `src/levelup/gui/` - PyQt6-based dashboard for monitoring and controlling runs
- **Tests**: `tests/unit/` and `tests/integration/` - Comprehensive test coverage with 507+ passing tests

### Key Architectural Patterns
- **Typer-based CLI**: All commands are defined as `@app.command()` decorated functions in `src/levelup/cli/app.py`
- **State persistence**: SQLite database at `~/.levelup/state.db` (configurable via `--db-path`) stores run records
- **StateManager CRUD**: Provides methods like `register_run()`, `update_run()`, `get_run()`, `list_runs()`, `delete_run()`
- **Interactive prompts**: Uses `prompt_toolkit` for interactive CLI experiences (task input, checkpoints, run selection)
- **Project context file**: `levelup/project_context.md` stores detected project info and recon findings
- **Resume pattern**: The `resume` command supports both explicit ID (`levelup resume <run-id>`) and interactive picker mode (`levelup resume`)
- **Git branching**: When `create_git_branch: true` (default), orchestrator creates branches named `levelup/{run_id}`

### Git Branch Management
- **Branch creation**: `Orchestrator._create_git_branch()` in `src/levelup/core/orchestrator.py` (line 556)
- **Current naming convention**: Hard-coded as `f"levelup/{run_id}"` (e.g., `levelup/a1b2c3d4`)
- **Branch checkout**: During resume, orchestrator checks out the run's branch if it exists (line 252)
- **Settings**: `PipelineSettings.create_git_branch` controls whether branches are created (default: `True`)

### Project Context Management
- **Module**: `src/levelup/core/project_context.py`
- **Functions**:
  - `write_project_context()`: Writes/overwrites project_context.md with detection results
  - `write_project_context_preserving()`: Updates detection header while preserving existing body content (recon data)
  - `read_project_context_body()`: Reads content below the detection header
  - `get_project_context_path()`: Returns path to `levelup/project_context.md`
- **File structure**:
  - Detection header: Language, Framework, Test runner, Test command (lines 1-6)
  - Body: "## Codebase Insights" and other sections (preserved across detection re-runs)
- **Used in detection step**: Orchestrator calls `write_project_context_preserving()` after detection (line 303)
- **Reading detection header**: Currently only `read_project_context_body()` exists; no function to read individual header fields (language, framework, etc.)
- **Header parsing**: Need to add function to parse header fields from project_context.md for reading branch naming convention

### CLI Command Patterns
- **Dual-mode commands**: Commands like `resume` support both explicit arguments and interactive selection when argument is omitted
- **Interactive pickers**: The `pick_resumable_run()` function in `prompts.py` displays a Rich table and prompts for selection by number or 'q' to quit
- **Confirmation dialogs**: Use `confirm_action()` from `prompts.py` for yes/no confirmations (e.g., GUI install)
- **Custom prompts**: Use `pt_prompt()` from `prompt_toolkit` for text input, supports multiline with Escape+Enter
- **Rich output**: Commands use Rich library for formatted tables, colored status badges, and styled console output
- **Error handling**: Use `print_error()` from `display.py` and `raise typer.Exit(1)` for error states
- **Banner display**: Most interactive commands call `print_banner()` at the start
- **StateManager kwargs**: Commands accept `--db-path` option and pass as `mgr_kwargs = {"db_path": db_path}` to StateManager
- **Run filtering**: Resume command filters runs by status: `r.status in ("failed", "aborted") and r.context_json`

### Testing Conventions
- Unit tests in `tests/unit/test_resume_rollback.py` cover resume/rollback CLI commands
- State manager tests in `tests/unit/test_state_manager.py` cover CRUD operations including `delete_run()`
- Project context tests in `tests/unit/test_project_context.py` cover read/write/preserve operations
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

### Relevant Files for Branch Naming Convention Task
- `src/levelup/core/orchestrator.py`: Contains `_create_git_branch()` method with hard-coded naming (line 563)
- `src/levelup/core/project_context.py`: Functions to read/write project_context.md
- `src/levelup/cli/prompts.py`: Contains interactive prompt utilities (can add new prompt function)
- `tests/unit/test_project_context.py`: Tests for project_context.py (template for new tests)
- `tests/unit/test_step_commits.py`: Tests for git branch creation (line 164-177)
- `levelup/project_context.md`: Target file for storing branch naming convention

### Branch Naming Convention Implementation Notes
- **First run detection**: Check if `branch_naming` field exists in project_context.md header
- **Prompt timing**: Prompt should occur in `Orchestrator.run()` before calling `_create_git_branch()` (around line 185)
- **Context field**: Add `branch_naming` field to `PipelineContext` model in `src/levelup/core/context.py`
- **Header format**: Add `- **Branch naming:** {convention}` after the test_command line in project_context.md
- **Placeholder substitution**: Support `{run_id}`, `{task_title}`, `{date}` placeholders in branch naming convention
- **Task title sanitization**: Convert to lowercase, replace spaces and special chars with hyphens, limit length (e.g., 50 chars)
- **Default convention**: Use `levelup/{run_id}` when field is missing (backward compatibility)
- **Resume/rollback**: Use stored convention from context to reconstruct branch name
- **Headless mode**: Skip prompt if running in headless mode; use existing convention or default
