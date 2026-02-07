# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Cost/token tracking** — each pipeline step records cost, token usage, duration, and turn count; pipeline summary and journal include cost breakdowns; `levelup status` shows cost per run
- **Step-level git commits** — auto-commits after each pipeline step (when `create_git_branch: true`), enabling atomic rollback to any step
- **`levelup resume`** command — resume a failed or aborted pipeline run from the step it failed at (or any earlier step with `--from-step`)
- **`levelup rollback`** command — roll back a run's changes via `git reset --hard` to a specific step commit or the pre-run state
- **Run journal** — each pipeline run writes an incremental Markdown log (`levelup/<date>-<task>.md`) with step details, checkpoint decisions, usage stats, and outcome
- `levelup version` command — displays installed version, git commit, and dirty state
- `levelup self-update` command — pulls latest code and reinstalls dependencies
- `uv.lock` dependency lockfile for reproducible installs
- Database schema versioning with automatic migrations
- `CHANGELOG.md` (this file)

### Changed
- `Backend.run_agent()` now returns `AgentResult` (was `str`) with cost/token/duration metadata
- `BaseAgent.run()` now returns `tuple[PipelineContext, AgentResult]` (was `PipelineContext`)
- `LLMClient.run_tool_loop()` now returns `ToolLoopResult` with accumulated token counts
- DB schema upgraded to v2 (adds `total_cost_usd` column to runs table)

## [0.1.0] - 2025-05-01

### Added
- TDD pipeline: detect → requirements → plan → test → code → review
- User checkpoints after requirements, test writing, and review steps
- Auto-detection for 14 languages, 18 frameworks, and their test runners
- Two backends: `claude_code` (default, zero-config) and `anthropic_sdk`
- Multi-instance support via SQLite state store
- Headless mode with `--headless` flag
- PyQt6 GUI dashboard (`levelup gui`)
- Terminal status view (`levelup status`)
- Configuration via YAML file, environment variables, and CLI flags
- Sandboxed file tools for safe AI agent operation
