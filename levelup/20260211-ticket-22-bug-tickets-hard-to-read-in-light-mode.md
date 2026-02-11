# Run Journal: Bug: Tickets hard to read in light mode

- **Run ID:** 0ebc406f19c1
- **Started:** 2026-02-11 19:32:45 UTC
- **Task:** Bug: Tickets hard to read in light mode
- **Ticket:** ticket:22 (ticket)

## Task Description

The title for tickets on the sidebar, when in the un-run state, is hard to read in light mode (gray on white background)
## Step: detect  (19:32:46)

See `levelup/project_context.md` for project details.
## Step: requirements  (19:34:01)

**Summary:** Improve readability of pending ticket text in light mode by using a darker color with better contrast against white background
- 3 requirement(s)
- 5 assumption(s)
- 6 out-of-scope item(s)
- **Usage:** 73.3s
### Checkpoint: requirements

- **Decision:** auto-approved
## Step: planning  (19:35:39)

**Approach:** Update the light theme pending ticket color from #4C566A to #2E3440 (darker shade matching the light theme's main text color) to improve readability and WCAG AA contrast compliance. This requires modifying the color constant in resources.py and updating test assertions to expect the new color value.
- 4 implementation step(s)
- **Affected files:** src/levelup/gui/resources.py, levelup/project_context.md
- **Risks:**
  - The new color #2E3440 matches the main text color in light theme, which may reduce visual distinction between pending tickets and other text elements, though this improves readability as requested
  - Users who have become accustomed to the lighter pending color may initially notice the change, though the improved contrast should be a net positive for usability
  - No test assertions need updating because existing tests focus on dark theme colors, but future tests for light theme pending colors should verify the new #2E3440 value
- **Usage:** 97.3s
