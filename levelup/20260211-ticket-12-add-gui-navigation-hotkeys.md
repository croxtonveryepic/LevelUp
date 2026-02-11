# Run Journal: Add GUI navigation hotkeys

- **Run ID:** 05f9d36ddad4
- **Started:** 2026-02-11 20:36:33 UTC
- **Task:** Add GUI navigation hotkeys
- **Ticket:** ticket:12 (ticket)

## Task Description

Since LevelUp is a tool for developers, many will expect there to be hotkeys to help them navigate and use the app. There should at least be one to jump to the next ticket waiting for user input (and focus the terminal). Create sensible default hotkeys for each functionality, and add page for hotkey customization.
## Step: detect  (20:36:33)

See `levelup/project_context.md` for project details.
## Step: requirements  (20:38:40)

**Summary:** Add keyboard navigation hotkeys to the LevelUp GUI dashboard with customizable keybindings
- 10 requirement(s)
- 6 assumption(s)
- 7 out-of-scope item(s)
- **Usage:** 125.7s
### Checkpoint: requirements

- **Decision:** auto-approved
## Step: planning  (20:40:45)

**Approach:** Implement keyboard navigation hotkeys using PyQt6's QShortcut mechanism with customizable keybindings persisted in the configuration system. The implementation follows a layered approach: (1) data model for hotkey settings in config layer, (2) hotkey registration and action handlers in MainWindow, (3) settings UI for customization, and (4) visual indicators via tooltips and help dialog. Each hotkey action will have platform-aware defaults (Ctrl on Windows/Linux, automatically translated to Cmd on macOS by Qt) and can be customized by the user through a dedicated settings interface.
- 9 implementation step(s)
- **Affected files:** src/levelup/config/settings.py, src/levelup/gui/main_window.py, src/levelup/gui/hotkey_settings_dialog.py, src/levelup/gui/hotkey_help_dialog.py, tests/unit/test_gui_hotkeys.py, tests/integration/test_gui_hotkey_settings.py
- **Risks:**
  - Keybinding conflicts: User-defined keybindings might conflict with Qt's built-in shortcuts or system shortcuts. The settings dialog should validate and warn about conflicts.
  - Platform differences: While Qt translates Ctrl to Cmd on macOS automatically, special keys (F1-F12, Escape) may have different system bindings across platforms. Testing on multiple platforms recommended.
  - Focus handling: Hotkeys for terminal focus (Ctrl+`) need to ensure proper widget focus transfer without disrupting terminal input. The terminal widget's keyPressEvent may capture some keys before shortcuts.
  - State consistency: Navigation hotkeys need to check current view state before acting. For example, 'next waiting ticket' should handle cases where no tickets are waiting gracefully without errors.
  - Settings migration: Existing installations won't have hotkey settings in their config. The code must handle missing hotkey settings gracefully with sensible defaults.
  - Hotkey registration timing: Shortcuts must be registered after MainWindow UI is fully built but before the window is shown, to ensure proper parent-child relationships.
  - Theme toggle persistence: The theme cycling hotkey must integrate with existing theme_manager.py functions to avoid state divergence between in-memory preference and persisted config.
- **Usage:** 122.7s
## Step: test_writing  (20:48:52)

Wrote 10 test file(s):
- `tests/unit/test_hotkey_settings.py` (new)
- `tests/unit/test_gui_hotkey_registration.py` (new)
- `tests/unit/test_gui_hotkey_actions.py` (new)
- `tests/unit/test_hotkey_settings_dialog.py` (new)
- `tests/unit/test_hotkey_tooltips.py` (new)
- `tests/unit/test_keyboard_shortcuts_help.py` (new)
- `tests/unit/test_hotkey_settings_toolbar.py` (new)
- `tests/unit/test_hotkey_edge_cases.py` (new)
- `tests/integration/test_hotkey_navigation.py` (new)
- `tests/integration/test_hotkey_settings_persistence.py` (new)
