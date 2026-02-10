---
model: haiku
---

Git add all files, commit with a provided message, and push.

## Arguments

$ARGUMENTS is the commit message. If empty, stop and report: "Please provide a commit message, e.g. `/push Fix login bug`."

## Instructions

1. If $ARGUMENTS is empty, stop and report: "Please provide a commit message, e.g. `/push Fix login bug`."

2. Run `git status` to check the working tree. If there are no changes (no untracked, modified, or staged files), stop and report: "Nothing to commit — working tree is clean."

3. Stage all changes:
   ```
   git add -A
   ```

4. Commit with the provided message:
   ```
   git commit -m "$ARGUMENTS"
   ```
   If the commit fails (e.g. pre-commit hook), stop and report the error.

5. Push to the remote tracking branch:
   ```
   git push
   ```
   If the current branch has no upstream, use:
   ```
   git push -u origin <current-branch>
   ```
   If push fails, report the error but note that the commit was created successfully.

6. Report the result: `Committed and pushed: "$ARGUMENTS"`
