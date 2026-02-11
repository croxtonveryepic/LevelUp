## [done] Light mode

Create a light theme for the gui. There should be a simple button to switch between light, dark, and match system theme, with the latter being the default.

## [done] Bug fix: usage doesn't track tokens

LevelUp tracks usage as in time consumed, but it should also provide information about token input and output.

## [done] Add a red test step

Add a step between test implementation and feature development to check that the new tests correctly fail before the feature is implemented.

## [done] Auto-approve

Create a project-level setting that determines whether to skip getting user approval for the requisite steps. Also allow individual tickets override this.

## [done] Bug fix: run tries to merge

User reports the following error at the end of a pipeline. The correct functionality is to publish the new branch, but not try to merge or delete it.

```
Branch 'levelup/38a8208a3590' is ready.
  git checkout levelup/38a8208a3590
  git merge levelup/38a8208a3590
Failed to remove worktree: Cmd('git') failed due to: exit code(255)
  cmdline: git worktree remove C:\Users\jccvae\.levelup\worktrees\38a8208a3590 --force
  stderr: 'error: failed to delete 'C:/Users/jccvae/.levelup/worktrees/38a8208a3590': Permission denied'
```

## [done] Light/Dark mode fixes

1. Default gui theme should be match system settings.
2. Gui theme selection should be an icon button instead of a dropdown.

## [done] Change sidebar in progress color

The color for in progress tickets (actively being run) should be blue (in a shade that is easy to see with the chosen color theme). It should switch to the current color for in progress (yellow-orange) while waiting for user input.

## [done] Bug: Terminal opens too soon

Integrated terminal should only be initialized when the ticket is run.

## [done] Bug: Resume button always disabled

The intended use of the resume button is to resume the run pipeline on tickets that have been paused. Review what the button currently does and when it is enabled to ensure correct functionality. Also, disable the run button while there is a pipeline that can be resumed.

## [done] Bug: Can't scroll up in integrated terminal

Users report that they can't scroll up in integrated terminals to review each step.
## [done] Record branch name

After a ticket is completed, the name of the newly-created branch should be recorded beneath the ticket.
## [done] Add GUI navigation hotkeys
<!--metadata
branch_name: levelup/add-gui-navigation-hotkeys
-->

Since LevelUp is a tool for developers, many will expect there to be hotkeys to help them navigate and use the app. There should at least be one to jump to the next ticket waiting for user input (and focus the terminal). Create sensible default hotkeys for each functionality, and add page for hotkey customization.
## [merged] Status Dropdown
<!--metadata
branch_name: levelup/status-dropdown
-->
Create a dropdown in the UI to force-change the status of a ticket. Include an option for "declined," which shows as green in the sidebar.
## Feature: Rich diff view
Users should be able to review changes from within the LevelUp GUI. Changes should be observable on a per-commit basis (so each step can be inspected individually) or the whole branch as a whole. Make sure this works while a run is in progress as well.
## Merge ticket from within UI
...then mark ticket as archived (put it in a different file) so it doesn't show on the sidebar

## [done] Bug: Tickets hard to read in light mode
<!--metadata
branch_name: levelup/task-title-in-kebab-case
-->
The title for tickets on the sidebar, when in the un-run state, is hard to read in light mode (gray on white background)

## [done] Bug: Integrated terminal always dark
<!--metadata
model: sonnet
branch_name: levelup/task-title-in-kebab-case
-->
Integrated terminal always has a light theme, even when the application theme is light.

## [done] Ticket form has fields that should be run options
<!--metadata
branch_name: levelup/task-title-in-kebab-case
-->
Tickets have options for auto-approve checkpoints, model choice, effort level, and whether to use planning. Really, these options are better suited to be associated with a run. Move the options down (to the left of the run button) and wire them up to be submitted when run is clicked. Lock these options while a run exists for the ticket.

## [done] Bug: Can't tab out of ticket description box
<!--metadata
branch_name: levelup/bug-can-t-tab-out-of-ticket-description-box
-->
User complains that the ticket description box inserts tab characters when tab is pressed, instead of the expected behavior of moving the focus onto the save button. Also confirm that shift-tab returns to the title box, enter submits (saves), and shift-enter inserts a newline.

## [merged] Bug: auto-approve checkpoints checkbox
<!--metadata
branch_name: levelup/bug-auto-approve-checkpoints-checkbox
-->
The auto-approve checkpoints checkbox should pre-populate with the project's default setting.

## [done] Bug: Failed to remove worktree
<!--metadata
branch_name: levelup/bug-failed-to-remove-worktree
-->
Users see an error at the end of every successful run. Worktrees should not be removed at the end of a run.

Branch 'levelup/add-gui-navigation-hotkeys' is ready.
To push to remote:
  git push origin levelup/add-gui-navigation-hotkeys
Or to merge into main:
  git checkout main && git merge levelup/add-gui-navigation-hotkeys
Failed to remove worktree: Cmd('git') failed due to: exit code(255)
  cmdline: git worktree remove C:\Users\jccvae\.levelup\worktrees\05f9d36ddad4 --force
  stderr: 'error: failed to delete 'C:/Users/jccvae/.levelup/worktrees/05f9d36ddad4': Permission denied'

## Bug: Cost breakdown does not show cost or token use

## [merged] Feature: Ticket descriptions should accept pasted images
<!--metadata
branch_name: levelup/feature-ticket-descriptions-should-accept-pasted-i
-->
Users should be able to paste images into ticket descriptions to highlight the issues they are seeing.

## [done] Bug: Copying texted in scrolled-up in integrated terminal
<!--metadata
branch_name: levelup/bug-copying-texted-in-scrolled-up-in-integrated-te
-->
When scrolled up in an integrated terminal, highlighting text and copying it to clipboard actually copies the text in the same relative position (area of the screen) at the very bottom of the terminal output instead of what appears to be highlighted.

## [done] Feature: Merge branch from within GUI
<!--metadata
branch_name: levelup/feature-merge-branch-from-within-gui
-->
When a pipeline is completed and a feature branch is ready to be reviewed and merged, naturally, users will want to merge their branch into master. Create an agent to handle merging a feature branch. The agent should always rebase the feature branch onto master first; it is expected that this may cause merge conflicts on project_context.md, the agent should make reasonable adjustments work through these merge conflicts. In the UI, there should be a button on the ticket page to kick off the merge agent. When it completes successfully, the ticket status should be moved from done to merged.

## [merged] Hide merged features by default
<!--metadata
branch_name: levelup/hide-merged-features-by-default
-->
Hide merged tickets from the sidebar list. Create a separate page for completed tickets.
