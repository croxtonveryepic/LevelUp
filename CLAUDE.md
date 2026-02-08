# CLAUDE.md — Instructions for AI Assistants

## Reminders

- **Keep README.md updated** when commands, flags, config options, or pipeline steps are added or changed.
- **Keep MEMORY.md updated** when architecture, dev workflow, or gotchas change.

## Project

LevelUp is an AI-Powered TDD Development Tool (Python CLI). It orchestrates Claude AI agents through a test-driven development pipeline: detect project → clarify requirements → plan → write tests → implement code → review.

## Dev Environment

- **Package manager:** uv (not pip/venv directly)
- **Python:** 3.13, Windows
- **Install:** `python -m uv pip install -e ".[dev]" --python .venv/Scripts/python.exe`
- **Run tests:** `.venv/Scripts/python.exe -m pytest tests/ -v`
- **Type check:** `.venv/Scripts/python.exe -m mypy src/`
- **Lint:** `.venv/Scripts/python.exe -m ruff check src/`

## Architecture

- Source code lives in `src/levelup/`
- Pipeline steps: detection → requirements → planning → test_writing → coding → security → review
- **Recon command**: `levelup recon` runs a standalone agent that deeply explores a project and writes enriched `levelup/project_context.md`; the detection step preserves this recon data on subsequent `levelup run` calls
- **Instruct feature**: at any checkpoint, user can type `(i)nstruct` to add a project rule to the target project's CLAUDE.md; the orchestrator reviews branch changes for violations, auto-fixes them, then re-prompts the checkpoint
- Agents use Anthropic tool-use loop (`agents/llm_client.py`)
- All file tools are sandboxed to the project directory
- User checkpoints after requirements, test_writing, security, and review steps
- Multi-instance: SQLite state store (`state/`) coordinates headless runs; GUI (`gui/`) monitors them
- `--headless` mode: checkpoints poll DB instead of terminal prompts
- State DB default: `~/.levelup/state.db`, override with `--db-path`

## Gotchas

- On Windows, `Path("/some/path")` produces backslashes — normalize with `.replace("\\", "/")` in test assertions
- Test output parser uses regex (`_extract_number_before`) — don't use naive `split()[0]`
- Classes named `Test*` (e.g. `TestResult`, `TestRunnerTool`) trigger pytest collection warnings — this is expected
