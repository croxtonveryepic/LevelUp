---
model: haiku
---

Check out a branch, rebase it onto master, then merge it into master and delete it.

## Arguments

$ARGUMENTS is the branch name to rebase and merge. If empty, stop and report: "Please provide a branch name, e.g. `/rebase-merge feature-xyz`."

## Instructions

1. If $ARGUMENTS is empty, stop and report: "Please provide a branch name, e.g. `/rebase-merge feature-xyz`."

2. Store the branch name as `BRANCH` (trim any whitespace from $ARGUMENTS).

3. Run `git status` to check for uncommitted changes. If there are any unstaged or staged changes, stop and report: "Cannot proceed: you have uncommitted changes. Please commit or stash them first."

4. Verify the branch exists:
   ```
   git rev-parse --verify BRANCH
   ```
   If it does not exist, stop and report: "Branch `BRANCH` does not exist."

5. Check out the branch:
   ```
   git checkout BRANCH
   ```

6. Rebase the branch onto master:
   ```
   git rebase master
   ```
   If the rebase fails due to conflicts, abort it (`git rebase --abort`) and stop with: "Rebase aborted: conflicts detected. Resolve them manually on `BRANCH` first."

7. Check out master:
   ```
   git checkout master
   ```

8. Merge the rebased branch into master with a fast-forward (since it was just rebased, this should be clean):
   ```
   git merge BRANCH
   ```
   If the merge fails, abort it (`git merge --abort`), switch back to the branch (`git checkout BRANCH`), and stop with: "Merge failed. Switched back to `BRANCH`."

9. Delete the merged branch:
   ```
   git branch -d BRANCH
   ```

10. Report the result: "Rebased `BRANCH` onto master, merged into master, and deleted `BRANCH`."
