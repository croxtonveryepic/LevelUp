# LevelUp

AI-Powered TDD Development Tool. LevelUp orchestrates Claude AI agents to perform test-driven development: it detects your project, clarifies requirements, writes tests first, implements code until tests pass, and reviews the result — with user checkpoints along the way.

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone and install
git clone <repo-url> && cd LevelUp
uv venv .venv
uv pip install -e ".[dev]" --python .venv/Scripts/python.exe   # Windows
# or
uv pip install -e ".[dev]" --python .venv/bin/python            # macOS/Linux

# GUI support (optional — installs PyQt6)
uv pip install -e ".[gui]" --python .venv/Scripts/python.exe
```

A `uv.lock` lockfile is included for reproducible installs. Run `uv sync` to install from the lockfile.

### Authentication

**Default (claude_code backend):** If you have [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated, no further setup is needed — LevelUp delegates to `claude -p` which handles auth internally.

**SDK backend:** Set your Anthropic API key if using `--backend anthropic_sdk`:

```bash
# Option 1: environment variable
export ANTHROPIC_API_KEY=sk-ant-...

# Option 2: config file (see Configuration below)
```

## Commands

### `levelup run` — Run the TDD pipeline

The main command. Give it a task and LevelUp handles the rest.

```bash
# Pass a task inline
levelup run "Add a /health endpoint that returns JSON status"

# Interactive mode (prompts for title + description)
levelup run

# Point at a different project
levelup run "Add pagination" --path /path/to/project

# Use a specific Claude model
levelup run "Fix the login bug" --model claude-opus-4-6

# Skip user checkpoints (fully automated)
levelup run "Add input validation" --no-checkpoints

# Limit how many code-fix iterations the agent can attempt
levelup run "Refactor auth module" --max-iterations 3
```

```bash
# Headless mode — checkpoints handled via GUI dashboard
levelup run "Add pagination" --headless

# Custom state DB path
levelup run "Fix bug" --db-path /tmp/my-state.db

# Use the Anthropic SDK backend (requires API key)
levelup run "Add feature" --backend anthropic_sdk
```

**Options:**

| Flag | Short | Description |
|------|-------|-------------|
| `--path PATH` | `-p` | Project directory (default: current dir) |
| `--model MODEL` | `-m` | Claude model override |
| `--no-checkpoints` | | Run without pausing for user approval |
| `--max-iterations N` | | Max test-fix cycles (default: 5) |
| `--headless` | | Run without terminal; checkpoints via GUI |
| `--db-path PATH` | | Override state DB path (default: `~/.levelup/state.db`) |
| `--backend NAME` | | Backend: `claude_code` (default) or `anthropic_sdk` |

**Pipeline steps:**

1. **Detect** — auto-detects language, framework, and test runner
2. **Requirements** — agent explores codebase and produces structured requirements
3. **Checkpoint** — you approve, revise, or reject the requirements
4. **Plan** — agent designs an implementation approach
5. **Test** — agent writes tests (TDD red phase)
6. **Checkpoint** — you review the tests
7. **Code** — agent implements code, runs tests, iterates until they pass (TDD green phase)
8. **Security** — agent detects vulnerabilities, auto-patches minor issues, flags major issues
9. **Checkpoint** — you review security findings (if major issues remain after auto-retry)
10. **Review** — agent checks for code quality and best practices
11. **Checkpoint** — you review the final changes
12. **Done** — summary shown with cost/token breakdown

When `create_git_branch: true` (default), LevelUp auto-commits after each step, giving you atomic rollback points. See `levelup rollback` below.

**Security step details:**

The security agent runs between coding and review to catch vulnerabilities before final approval:

- **Auto-patching:** Minor issues (INFO/WARNING severity) like missing input validation, weak defaults, or missing type hints are automatically fixed using Write/Edit tools
- **Automatic loop-back:** Major issues (ERROR/CRITICAL severity) like SQL injection, XSS, hardcoded secrets, or weak crypto trigger an automatic re-run of the coding agent with security feedback
- **One retry limit:** If issues remain after one automatic retry, the pipeline continues to the checkpoint for manual review
- **OWASP Top 10 coverage:** Checks for injection attacks, authentication flaws, crypto weaknesses, input validation gaps, and insecure configurations
- **CWE references:** Findings include Common Weakness Enumeration IDs for tracking and remediation

At each checkpoint you can:
- **(a)pprove** — continue to the next step
- **(r)evise** — provide feedback and re-run the step
- **(x) reject** — abort and roll back

### `levelup recon` — Project reconnaissance

Run a one-time deep exploration of a project codebase. The recon agent examines directory structure, architecture, coding conventions, dependencies, and test patterns, then writes its findings to `levelup/project_context.md`. Subsequent `levelup run` calls preserve this enriched context.

```bash
levelup recon
levelup recon --path /path/to/project
levelup recon --model claude-opus-4-6
levelup recon --backend anthropic_sdk
```

**Options:**

| Flag | Short | Description |
|------|-------|-------------|
| `--path PATH` | `-p` | Project directory (default: current dir) |
| `--model MODEL` | `-m` | Claude model override |
| `--backend NAME` | | Backend: `claude_code` (default) or `anthropic_sdk` |

### `levelup detect` — Detect project info

Analyzes a project directory and reports what it found. Useful for verifying detection before running the full pipeline.

```bash
levelup detect
levelup detect --path /path/to/project
```

**Example output:**

```
┌─────────────────────────────┐
│     Project Detection       │
├────────────┬────────────────┤
│ Language   │ python         │
│ Framework  │ fastapi        │
│ Test Runner│ pytest         │
│ Test Cmd   │ pytest         │
└────────────┴────────────────┘
```

**Supported languages:** Python, JavaScript, TypeScript, Go, Rust, Java, Kotlin, Ruby, Elixir, PHP, Swift, C#, C, C++

**Supported frameworks:** Django, FastAPI, Flask, Next.js, React, Vue, Angular, Express, Vite, Nuxt, Rails, Sinatra, Gin, Echo, Actix, Axum, Rocket, Spring

### `levelup gui` — Launch the GUI dashboard

Opens a PyQt6 desktop window to monitor and control all running LevelUp instances. Requires the `gui` extra (`pip install "levelup[gui]"`).

```bash
levelup gui
levelup gui --db-path /tmp/my-state.db
```

The dashboard:
- Shows all runs (active, waiting, completed, failed) with colored status badges
- Auto-refreshes every 2 seconds
- Double-click a "Needs Input" row to open the checkpoint dialog (approve/revise/reject)
- Right-click for details or to remove finished runs
- "Clean Up" button removes all completed/failed/aborted runs

### `levelup status` — Show run status in terminal

Prints a Rich table of all tracked runs. Useful when you don't have a GUI available.

```bash
levelup status
levelup status --db-path /tmp/my-state.db
```

### `levelup resume` — Resume a failed run

Pick up a failed or aborted pipeline run from where it left off (or from an earlier step).

```bash
# Resume from the step that failed
levelup resume <run-id>

# Resume from a specific earlier step
levelup resume <run-id> --from-step planning

# With overrides
levelup resume <run-id> --model claude-opus-4-6 --backend anthropic_sdk
```

**Options:**

| Flag | Short | Description |
|------|-------|-------------|
| `--from-step STEP` | | Step to resume from (default: where it failed) |
| `--path PATH` | `-p` | Project directory (default: current dir) |
| `--model MODEL` | `-m` | Claude model override |
| `--backend NAME` | | Backend override |
| `--db-path PATH` | | Override state DB path |

### `levelup rollback` — Roll back a run

Undo changes from a pipeline run by resetting git to a previous state. Requires that the run was made with `create_git_branch: true`.

```bash
# Roll back to the state before the run started
levelup rollback <run-id>

# Roll back to a specific step's commit
levelup rollback <run-id> --to test_writing
```

**Options:**

| Flag | Description |
|------|-------------|
| `--to STEP` | Roll back to this step's commit (default: pre-run state) |
| `--db-path PATH` | Override state DB path |

### `levelup config` — Show configuration

Displays the active configuration after merging all sources.

```bash
levelup config
levelup config --path /path/to/project
```

### `levelup version` — Show installed version

Displays the installed version, git commit hash, and working tree status.

```bash
levelup version
# levelup 0.1.0 (commit abc1234, clean)
```

### `levelup self-update` — Update LevelUp

Pulls the latest code from git and reinstalls dependencies. Requires that LevelUp was installed from a git clone.

```bash
levelup self-update
```

## Configuration

Settings are layered with this precedence (highest wins):

**CLI flags > environment variables > config file > defaults**

### Config file

Create `levelup.yaml` (or `.levelup.yaml`) in your project root:

```yaml
llm:
  model: claude-sonnet-4-5-20250929
  max_tokens: 8192
  temperature: 0.0
  backend: claude_code         # "claude_code" (default) or "anthropic_sdk"
  claude_executable: claude    # path to claude binary (for claude_code backend)
  api_key: sk-ant-...          # only needed for anthropic_sdk backend

project:
  language: python              # override auto-detection
  framework: fastapi            # override auto-detection
  test_command: pytest -x       # override auto-detection

pipeline:
  max_code_iterations: 5
  require_checkpoints: true
  create_git_branch: true
  auto_commit: false

ticket_source: manual
```

All fields are optional — only set what you want to override.

### Environment variables

All settings can be set via `LEVELUP_`-prefixed env vars with `__` as the nesting separator:

```bash
ANTHROPIC_API_KEY=sk-ant-...
LEVELUP_LLM__MODEL=claude-opus-4-6
LEVELUP_LLM__MAX_TOKENS=16384
LEVELUP_PIPELINE__MAX_CODE_ITERATIONS=10
LEVELUP_PIPELINE__REQUIRE_CHECKPOINTS=false
```

## Running as a module

```bash
python -m levelup run "Add a feature"
python -m levelup detect --path .
```

## Development

```bash
# Run tests
.venv/Scripts/python.exe -m pytest tests/ -v

# Run with coverage
.venv/Scripts/python.exe -m pytest tests/ --cov=levelup --cov-report=term-missing

# Type checking
.venv/Scripts/python.exe -m mypy src/

# Linting
.venv/Scripts/python.exe -m ruff check src/
```

## Project Structure

```
src/levelup/
  cli/          Commands (run, detect, config, gui, status), Rich display, prompts
  core/         Orchestrator, pipeline definitions, context models, checkpoints
  agents/       Backend protocol, LLM client, claude -p client, base agent, recon agent, and 5 specialized agents
  tools/        Sandboxed file read/write/search, shell execution, test runner
  detection/    Language, framework, and test runner auto-detection
  config/       Pydantic Settings models, config file loader
  state/        SQLite state store for multi-instance coordination
  gui/          PyQt6 dashboard — main window, checkpoint dialog, styles
  tickets/      Ticket source plugin system (manual input for MVP)
```

## Multi-Instance Support

LevelUp supports running multiple pipeline instances simultaneously. Each `levelup run` (including `--headless`) registers in a shared SQLite database (`~/.levelup/state.db`). The `levelup gui` dashboard reads this DB to show all runs and handle checkpoints.

**Architecture:**
- Each run is an independent OS process
- SQLite with WAL mode is the sole coordination mechanism (no sockets)
- GUI is a separate process that reads/writes the same DB
- Dead processes are automatically detected via PID checking
