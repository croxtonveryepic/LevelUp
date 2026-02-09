# Run Journal: Branch name convention option

- **Run ID:** bd335a88e2ef
- **Started:** 2026-02-09 22:38:48 UTC
- **Task:** Branch name convention option

## Task Description

The first time levelup run is used in a project, the user should be prompted to provide information about how branches should be named. This information should then be stored in project_context.md and followed when creating branches.
## Step: detect  (22:38:48)

See `levelup/project_context.md` for project details.
## Step: requirements  (22:40:35)

**Summary:** Enable users to configure branch naming conventions on first run, store the convention in project_context.md, and use it when creating git branches
- 7 requirement(s)
- 7 assumption(s)
- 6 out-of-scope item(s)
- **Usage:** 105.1s
### Checkpoint: requirements

- **Decision:** approve
## Step: planning  (22:43:48)

**Approach:** Add configurable branch naming convention by: (1) extending project_context.md to store branch naming pattern in header, (2) adding read function to parse header fields, (3) prompting user on first run to choose convention, (4) storing convention in PipelineContext, (5) using convention in _create_git_branch() with placeholder substitution, and (6) ensuring resume/rollback work with custom branch names.
- 18 implementation step(s)
- **Affected files:** src/levelup/core/context.py, src/levelup/core/project_context.py, src/levelup/core/orchestrator.py, src/levelup/cli/prompts.py, src/levelup/cli/app.py, tests/unit/test_project_context.py, tests/unit/test_step_commits.py, tests/unit/test_branch_naming.py, tests/unit/test_prompts_branch_naming.py, tests/integration/test_branch_naming_flow.py
- **Risks:**
  - Backward compatibility: existing runs without branch_naming field must default to 'levelup/{run_id}' pattern
  - Headless mode: must skip interactive prompt and use existing convention or default
  - Resume/rollback: branch name reconstruction must match original branch created during run()
  - Placeholder validation: invalid placeholders or convention strings could break branch creation
  - Git branch name constraints: sanitized task titles must comply with git branch naming rules (no spaces, special chars)
  - First-run detection timing: prompt must occur before branch creation but after detection step completes
  - Context serialization: branch_naming field must survive JSON serialization in state DB
  - Project context file parsing: header parsing logic must be robust to variations in whitespace and formatting
- **Usage:** 129.9s
## Step: test_writing  (22:49:24)

No test files written.
### Checkpoint: test_writing

- **Decision:** approve
## Step: coding  (22:58:11)

- **Code iterations:** 0
- **Test results:** 0 total, 0 failures, 0 errors (FAILED)
## Step: security  (22:59:37)

Step `security` completed.
- **Usage:** 84.1s
### Checkpoint: security

- **Decision:** approve
## Step: review  (23:00:19)

No review findings.
