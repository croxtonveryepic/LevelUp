## [done] Light mode

Create a light theme for the gui. There should be a simple button to switch between light, dark, and match system theme, with the latter being the default.

## [in progress] Bug fix: usage doesn't track tokens

LevelUp tracks usage as in time consumed, but it should also provide information about token input and output.

## Add a red test step

Add a step between test implementation and feature development to check that the new tests correctly fail before the feature is implemented.

## Auto-approve

Create a project-level setting that determines whether to skip getting user approval for the requisite steps. Also allow individual tickets override this.

## Bug fix: run tries to merge

User reports the following error at the end of a pipeline. The correct functionality is to publish the new branch, but not try to merge or delete it.

```
Branch 'levelup/38a8208a3590' is ready.
  git checkout levelup/38a8208a3590
  git merge levelup/38a8208a3590
Failed to remove worktree: Cmd('git') failed due to: exit code(255)
  cmdline: git worktree remove C:\Users\jccvae\.levelup\worktrees\38a8208a3590 --force
  stderr: 'error: failed to delete 'C:/Users/jccvae/.levelup/worktrees/38a8208a3590': Permission denied'
```

## Light/Dark mode fixes

1. Default gui theme should be match system settings.
2. Gui theme selection should be an icon button instead of a dropdown.
