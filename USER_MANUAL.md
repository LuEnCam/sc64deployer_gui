# sc64deployer GUI — User Manual

## Overview
sc64deployer GUI is a PyQt6 front-end for `sc64deployer` that helps you interact with SummerCart64 (SC64) devices. It exposes the deployer commands via clickable buttons, options, and parameter inputs. The GUI also supports version checks and downloading/updating sc64deployer and sc64menu.n64.

## Requirements
- Windows / Linux / macOS (Python supported platform)
- Python 3.8+ with these packages:
  - PyQt6
  - requests
  - packaging

(These are inferred from the code imports in `main.py`.)

## Installation
1. Create a Python virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
# or
source .venv/bin/activate       # macOS / Linux
```

2. Install dependencies:

```powershell
pip install PyQt6 requests packaging
```

3. Run the GUI locally:

```powershell
python main.py
```

## Packaging (distributable executable)
To build a single-file executable (example from repo context):

```powershell
pyinstaller.exe --onefile --noconsole --add-data "sc64.ico;." --name sc64deployer_gui --icon=sc64.ico main.py
```

This bundles the icon `sc64.ico` next to the executable. Adjust flags as needed for your target OS.

## Starting the App
- Launch the app with `python main.py` or run the packaged executable.
- On first run the app attempts to restore saved settings (window size, last `sc64deployer` path).

## Main Window and Workflow
- Menu: Use the `File` menu → *Select sc64deployer* to choose your `sc64deployer` binary/executable.
  - On Windows the file dialog filters for `*.exe`.
  - The status bar shows the selected deployer path and the deployer version (if detected).
- Commands: The left column shows available high-level commands (e.g., `list`, `upload`, `64dd`, `sd`, `info`, `reset`, `set`, `firmware`, `test`, `server`, `help`, `--version`). Click a command to populate available options.
- Options: After picking a command, available options appear below; click an option to open parameter inputs if required.
- Parameters: Parameter inputs vary by type (text box, file selector, spinner, radio-like buttons). For example:
  - File selection buttons open a file chooser and then enable the `Run Command` button with the composed arguments.
  - For upload/download operations the GUI provides a ROM file selector.
- Run: When parameters are valid the `Run Command` button enables (green). Click to execute the selected command via the `sc64deployer` executable.
- Output: Program output and errors are shown in the `Sc64deployer Output` pane (read-only).

## Commands and Options (summary)
The GUI maps to `sc64deployer` commands defined in `sc64_lists_command_options.py`. Important commands include:
- `list` — list connected SC64 devices
- `upload` — upload a ROM to SC64 (supports save options, TV type, direct boot, etc.)
- `64dd` — upload IPL and disk images for 64DD (supports multiple disk arguments)
- `debug` — enter debug mode (many debug options supported)
- `dump` — dump memory ranges to file
- `sd` — SD card operations (`ls`, `stat`, `mv`, `rm`, `download`, `upload`, `mkfs`)
- `info`, `reset`, `set`, `firmware`, `test`, `fifo-read`, `server`, `help`, `--version`

Refer to the option list in `sc64_lists_command_options.py` for precise option names and parameter types (radio lists, spinner ranges, path selectors, etc.).

## Example Flows
- Upload a ROM:
  1. `File` → *Select sc64deployer* (choose your `sc64deployer.exe` or binary).
  2. Click `upload` command.
  3. If shown, click the default upload button or add options like `--save` and select a save file.
  4. Select the ROM file via the provided file selector.
  5. Click `Run Command`.

- Downloading a file from SD card:
  1. Select the `sd` command, then the `download` option.
  2. Enter/select the SD path and choose a local destination via the "Save File As..." control.
  3. Click `Run Command`.

## Update Checking
- The `Help` menu contains actions to verify updates:
  - Verify update for `sc64deployer` — checks GitHub releases and prompts to download and extract a new release.
  - Verify update for `sc64menu.n64` — downloads `sc64menu.n64` from releases and can upload it to the SD card.
- When an update is available the app can download archives and extract them to a user-chosen folder.

## Logs & Errors
- Output (stdout/stderr) from `sc64deployer` is appended to the GUI output pane.
- If a command is already running the GUI prevents running another concurrent command and shows an error message.

## Settings Persistence
- Window size and the selected `sc64deployer` path are stored via `QSettings` and restored on next run.

## Troubleshooting
- "Please select sc64deployer.exe first." — Select the `sc64deployer` executable using the `File` menu.
- Invalid deployer selection — If you pick a binary whose filename does not contain `sc64deployer`, the GUI shows an error and resets the selection.
- Network/timeouts when checking updates — Ensure internet connectivity; the app uses GitHub API requests with timeouts.
- If extraction of downloaded archives fails, ensure the destination folder is writable and you have enough disk space.

## Security & Notes
- The GUI executes the selected `sc64deployer` binary; ensure you trust the binary before running.
- When saving temporary files, the application may use your system temp directory.

## FAQ
Q: Can I use this GUI without a local `sc64deployer` binary?
A: No — the GUI requires a compatible `sc64deployer` executable; use the `File` menu to select it.

Q: What file types are supported for ROM uploads?
A: The GUI filters common ROM file extensions such as `.z64`, `.n64`, `.v64`, `.bin` in file dialogs.

Q: How do I update `sc64menu.n64` on the SD card?
A: Use `Help` → *Verify update for sc64menu.n64*, confirm the download, and allow the app to upload it to `/sc64menu.n64` on the SD card.

## Developer Notes (for contributors)
- Main UI: `main.py` — contains `SC64MainWidget` (UI logic) and `SC64MainWindow` (app bootstrap).
- Commands/options: `sc64_lists_command_options.py` — central listing used to build command and option buttons.
- Worker: `exec_runner.py` provides `ExecWorker` used to run the external `sc64deployer` binary on a background thread.
- Updating behavior: GitHub API endpoints are configured in `main.py` constants `SC64_GITHUB_API_LATEST` and `SC64MENU_GITHUB_API_LATEST`.

## Contact / Further Help
If you want a condensed Quick Start, a printable PDF, translations, or embedding more inline help in the GUI, tell me which you'd like and I will prepare it.

---
Generated from repository sources: `main.py` and `sc64_lists_command_options.py`.
