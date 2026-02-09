Increment the LevelUp version number.

## Arguments

$ARGUMENTS should be one of: `major`, `minor`, or `patch` (default: `patch` if no argument given).

## Instructions

1. Read the current version from `src/levelup/__init__.py` (the `__version__` variable) and `pyproject.toml` (the `version` field under `[project]`). They must match — if they don't, stop and report the mismatch.

2. Parse the current version as `MAJOR.MINOR.PATCH` (semver without pre-release).

3. Compute the new version based on the bump type from $ARGUMENTS:
   - `patch` (default): increment PATCH, e.g. `0.1.1` → `0.1.2`
   - `minor`: increment MINOR, reset PATCH to 0, e.g. `0.1.1` → `0.2.0`
   - `major`: increment MAJOR, reset MINOR and PATCH to 0, e.g. `0.1.1` → `1.0.0`

4. Update both files with the new version:
   - In `src/levelup/__init__.py`: update the `__version__ = "X.Y.Z"` line
   - In `pyproject.toml`: update the `version = "X.Y.Z"` line under `[project]`

5. Report the change: `Version bumped: OLD → NEW`
