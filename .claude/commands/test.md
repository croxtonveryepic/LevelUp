---
model: haiku
---

Run the full test suite.

## Arguments

$ARGUMENTS is an optional filter string (e.g. a test file path, `-k` expression, or marker). If empty, run all tests.

## Instructions

1. Build the pytest command:
   - Base: `.venv/Scripts/python.exe -m pytest tests/ -v`
   - If $ARGUMENTS is provided, append it to the command (e.g. `.venv/Scripts/python.exe -m pytest tests/ -v $ARGUMENTS`)

2. Run the command.

3. Report a concise summary:
   - Total passed, failed, skipped, errors
   - If there are failures, list each failing test name and a one-line reason
   - Final line: `All tests passed.` or `X test(s) failed.`
