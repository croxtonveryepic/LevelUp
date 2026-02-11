# Run Journal: Bug: Failed to remove worktree

- **Run ID:** 3a4b0b8bdb63
- **Started:** 2026-02-11 20:59:30 UTC
- **Task:** Bug: Failed to remove worktree
- **Ticket:** ticket:21 (ticket)

## Task Description

Users see an error at the end of every successful run. Worktrees should not be removed at the end of a run.

Branch 'levelup/add-gui-navigation-hotkeys' is ready.
To push to remote:
  git push origin levelup/add-gui-navigation-hotkeys
Or to merge into main:
  git checkout main && git merge levelup/add-gui-navigation-hotkeys
Failed to remove worktree: Cmd('git') failed due to: exit code(255)
  cmdline: git worktree remove C:\Users\jccvae\.levelup\worktrees\05f9d36ddad4 --force
  stderr: 'error: failed to delete 'C:/Users/jccvae/.levelup/worktrees/05f9d36ddad4': Permission denied'
## Step: detect  (20:59:30)

See `levelup/project_context.md` for project details.
