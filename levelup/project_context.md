# Project Context

- **Language:** python
- **Framework:** none
- **Test runner:** pytest
- **Test command:** pytest
- **Branch naming:** levelup/task-title-in-kebab-case
- **Placeholder substitution**: Support `{run_id}`, `{task_title}`, `{date}` placeholders in branch naming convention
- **Task title sanitization**: Convert to lowercase, replace spaces and special chars with hyphens, limit length (e.g., 50 chars)
- **Default convention**: Use `levelup/{run_id}` when field is missing (backward compatibility)
- **Resume/rollback**: Use stored convention from context to reconstruct branch name
- **Headless mode**: Skip prompt if running in headless mode; use existing convention or default
