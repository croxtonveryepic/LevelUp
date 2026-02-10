---
model: haiku
---

Bump the version, commit with a message, and push.

## Arguments

$ARGUMENTS is an optional commit message. If no argument is given, the commit message defaults to `bump version to X.Y.Z`.

## Instructions

1. Run the /bump-version skill with `patch` to increment the version. Note the new version number X.Y.Z.

2. Determine the commit message:
   - If $ARGUMENTS is provided and non-empty, use it as the commit message.
   - Otherwise, use: `bump version to X.Y.Z`

3. Run the /push skill with the determined commit message.
