# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `levelup version` command — displays installed version, git commit, and dirty state
- `levelup self-update` command — pulls latest code and reinstalls dependencies
- `uv.lock` dependency lockfile for reproducible installs
- Database schema versioning with automatic migrations
- `CHANGELOG.md` (this file)

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
