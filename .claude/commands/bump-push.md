---
model: haiku
---

Bump the version and then commit and push the change.

## Arguments

$ARGUMENTS should be one of: `major`, `minor`, or `patch` (default: `patch` if no argument given).

## Instructions

1. Run the /bump-version skill with $ARGUMENTS to increment the version.

2. After the version is bumped, run the /push skill with the commit message: `bump version to X.Y.Z` (where X.Y.Z is the new version number from step 1).
