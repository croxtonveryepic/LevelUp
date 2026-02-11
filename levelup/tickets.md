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

## Bug: Database schema error
│   131 │   │   conn.commit()                                                                    │ db_path = WindowsPath('C:/Users/jccvae/.levelup/state.db')  │                │
│ ❱ 132 │   │   _run_migrations(conn)                                                            ╰─────────────────────────────────────────────────────────────╯                │
│   133 │   finally:                                                                                                                                                            │
│   134 │   │   conn.close()                                                                                                                                                    │
│   135                                                                                                                                                                         │
│                                                                                                                                                                               │
│ C:\Users\jccvae\AppData\Roaming\uv\tools\levelup\Lib\site-packages\levelup\state\db.py:99 in _run_migrations                                                                  │
│                                                                                                                                                                               │
│    96 │   current = _get_schema_version(conn)                                                  ╭────────────────────────── locals ───────────────────────────╮                │
│    97 │                                                                                        │    conn = <sqlite3.Connection object at 0x000002D601DF7F10> │                │
│    98 │   if current > CURRENT_SCHEMA_VERSION:                                                 │ current = 5                                                 │                │
│ ❱  99 │   │   raise RuntimeError(                                                              ╰─────────────────────────────────────────────────────────────╯                │
│   100 │   │   │   f"Database schema version {current} is newer than the code supports "                                                                                       │
│   101 │   │   │   f"(max {CURRENT_SCHEMA_VERSION}). Please upgrade LevelUp."                                                                                                  │
│   102 │   │   )                                                                                                                                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
RuntimeError: Database schema version 5 is newer than the code supports (max 4). Please upgrade LevelUp.

## Bug: Active run exists
User reports getting a pop-up error stating that an active run already exists. He states that the ticket is done and he did not do anything that would create another run for that ticket.

---------------------------
Active Run Exists
---------------------------
Ticket #2 already has an active run (<MagicMock name='mock.get_run().run_id.__getitem__()' id='1979491656640'>, status=aborted).
Resume or forget it first.
---------------------------
OK   
---------------------------

## [done] Record branch name
After a ticket is completed, the name of the newly-created branch should be recorded beneath the ticket.

## Create command to change branch naming convention
We already have a function to prompt a user for a branch naming convention. Let's add a command that lets them do this ahead of time, or to run it later to change the naming convention.

## [in progress] Add GUI navigation hotkeys
Since LevelUp is a tool for developers, many will expect there to be hotkeys to help them navigate and use the app. There should at least be one to jump to the next ticket waiting for user input (and focus the terminal). Create sensible default hotkeys for each functionality, and add page for hotkey customization.
## [in progress] Bug: Incorrect color for tickets in sidebar
Sidebar tickets should be blue while thinking and turn yellow-orange when they reach a checkpoint. Create an additional ticket status if necessary.
