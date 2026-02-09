---
model: haiku
---

Merge the current branch into master and delete it.

## Instructions

1. Run `git status` to check for uncommitted changes. If there are any unstaged or staged changes, stop and report: "Cannot merge: you have uncommitted changes. Please commit or stash them first."

2. Run `git branch --show-current` to get the current branch name. If the current branch is `master`, stop and report: "Already on master — nothing to merge."

3. Store the branch name (call it `BRANCH`).

4. Switch to master:
   ```
   git checkout master
   ```

5. Pull the latest master from origin (skip if no remote is configured):
   ```
   git pull origin master
   ```
   If `git remote` returns nothing, skip this step.

6. Merge the branch into master with a merge commit:
   ```
   git merge BRANCH --no-ff -m "Merge branch 'BRANCH' into master"
   ```
   If the merge fails due to conflicts, abort it (`git merge --abort`), switch back to the original branch (`git checkout BRANCH`), and stop with: "Merge aborted: conflicts detected. Resolve them on `BRANCH` first."

7. Delete the merged branch:
   ```
   git branch -d BRANCH
   ```

8. Report the result: `Merged BRANCH into master and deleted BRANCH.`
