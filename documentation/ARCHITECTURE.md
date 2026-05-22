# Architecture — sc64deployer_gui

## Overview

sc64deployer_gui is a PyQt6 desktop application that wraps the [SummerCart64](https://github.com/Polprzewodnikowy/SummerCart64) `sc64deployer` CLI tool in a graphical interface. It targets N64 hobbyists and developers who prefer a point-and-click workflow over the command line.

The application dynamically generates UI controls (buttons, file pickers, text inputs) from a data-driven command/option/parameter schema, executes the `sc64deployer` binary in a background thread, and streams output back to the GUI.

## Dependencies

| Package | Purpose |
|---------|---------|
| PyQt6 | GUI framework (widgets, threading, settings persistence) |
| requests | HTTP calls to the GitHub Releases API for update checks |
| packaging | Semantic version comparison during update checks |

No `requirements.txt` or `pyproject.toml` exists yet. Install manually:

```
pip install PyQt6 requests packaging
```

## File Map

```
sc64deployer_gui/
├── main.py                          # Application entry point, UI, update logic
├── sd_explorer.py                   # SD Card file explorer widget (tree, drag & drop)
├── exec_runner.py                   # Background worker for subprocess execution
├── sc64_lists_command_options.py     # Data-driven command/option/parameter definitions
├── sc64deployer_gui.spec            # PyInstaller build spec
├── 64dd_ipl/                        # 64DD IPL files
├── Notes.md                         # Linux sudoers setup notes
├── README.md                        # Project overview and quick start
└── USER_MANUAL.md                   # End-user manual
```

## Module Details

### main.py (~950 lines)

Contains two classes:

#### `SC64MainWidget(QWidget)`

The central widget. Responsible for:

- **Tab interface** — uses `QTabWidget` with a Commands tab and an SD Card Explorer tab.
- **Dynamic UI generation** — iterates `list_of_commands`, `list_of_options`, and `list_of_parameters` to create buttons and input controls at runtime.
- **Command composition** — assembles a CLI invocation string from the selected command, options, and parameters. Uses `shlex.quote()` for argument escaping.
- **Process management** — creates `ExecWorker` + `QThread` pairs for each invocation; enforces single-command-at-a-time execution.
- **Update checking** — queries GitHub Releases API for `sc64deployer`, `sc64menu.n64`, and SC64 firmware; downloads, extracts, and applies updates.
- **sc64menu version detection** — downloads `sc64menu.n64` from the SD card and scans for hard-coded hex patterns to extract an embedded build date.
- **SD Explorer integration** — initializes `SDCardExplorer` when a valid deployer is selected and adds it as a tab.

#### `SC64MainWindow`

Application bootstrap (not a `QMainWindow` subclass — uses composition). Sets up:

- Menu bar: `File` → Select deployer; `Help` → Update checks.
- Status bar: displays selected deployer path.
- `QSettings` persistence for window size and deployer path.
- Entry point at module level: instantiates `SC64MainWindow` and calls `run()`.

### exec_runner.py (~60 lines)

#### `ExecWorker(QObject)`

Runs `sc64deployer` in a subprocess on a `QThread`.

**Signals:**
- `output(str)` — emitted per stdout line
- `error(str)` — emitted with stderr content
- `finished()` — emitted when the process completes

**Execution flow:**
1. Builds command list: `[exe_path, command, *options]` (prepends `sudo -n` on Linux).
2. Opens `subprocess.Popen` with piped stdout/stderr/stdin.
3. For `firmware update`, writes `"y\n"` to stdin to auto-confirm.
4. Reads stdout line-by-line, then reads stderr in bulk.
5. Emits `finished()` to trigger thread cleanup.

### sc64_lists_command_options.py (~120 lines)

Data definitions that drive the UI:

- **`Types` enum** — classifies parameter input types (`TEXT`, `PATH_GET_LOCATION`, `RADIO`, `SPINNER`, `ADDRESS`, etc.).
- **`list_of_commands`** — `[name, description]` pairs for all supported `sc64deployer` commands.
- **`list_of_options`** — `[command, option_flag, arg_count, Types, description]` tuples. The UI generates option buttons scoped to the selected command.
- **`list_of_parameters`** — `[command, option_flag, [values]]` tuples for radio-style choices (save types, TV types).

### sd_explorer.py (~1,150 lines)

The SD Card file explorer, integrated as a tab in the main window via `QTabWidget`.

#### `SDCardExplorer(QWidget)`

Tree-based file browser for the SC64's SD card. Provides:

- **File tree display** — `QTreeWidget` with Name, Type, and Size columns.
- **Navigation** — double-click folders, ".." parent traversal, manual path entry.
- **File operations** — download, upload, rename, delete via `SDOperationWorker`.
- **Drag & drop** — platform-specific implementation:
  - macOS: native file promises (`_SDFilePromiseDelegate`, `_NativeDragSource`) for instant drag start with lazy download.
  - Windows/Linux: `_LazyDownloadMimeData` for on-demand file download during drop.
- **Context menu** — right-click for quick actions on selected items.

**Signals:**
- `operation_completed()` — emitted when any SD operation finishes
- `status_changed(str)` — status updates forwarded to the main window status bar

#### `SDOperationWorker(QObject)`

Async subprocess executor for SD card commands. Runs `sc64deployer sd <subcommand> <args>` on a `QThread`, emitting `output`, `error`, and `finished` signals.

#### `SDFileItem`

Data class representing an SD card entry: `name`, `path`, `is_dir`, `size`, `children`.

#### `SDOperationType` (Enum)

Operation identifiers: `LIST`, `DOWNLOAD`, `UPLOAD`, `RENAME`, `DELETE`, `MKDIR`.

#### Integration with `main.py`

`SC64MainWidget._init_sd_explorer()` creates an `SDCardExplorer` instance and adds it as the second tab. The explorer's `status_changed` signal is connected to the main window's status bar.

> For detailed architecture diagrams, see [ARCHITECTURE_SD_EXPLORER.md](ARCHITECTURE_SD_EXPLORER.md).

## Data Flow

```
User clicks command → list_options() generates option buttons
  → User clicks option → list_parameters() generates parameter inputs
    → User fills parameters → enable_run_button() arms "Run Command"
      → User clicks "Run Command" → run_command() → start_worker()
        → ExecWorker.run() on QThread → subprocess.Popen(sc64deployer ...)
          → stdout lines → output signal → append_output() → QTextEdit
          → stderr → error signal → append_error() → QTextEdit
          → finished signal → process_finished() → re-enable buttons
```

## Threading Model

- One `QThread` + one `ExecWorker` at a time. Attempts to run a second command while one is active are rejected with an error message.
- `ExecWorker` is moved to the thread via `moveToThread()`. New instances are created for each invocation to avoid Qt's "cannot move to a new thread" restriction.
- Cleanup chain: `worker.finished` → `thread.quit` → `worker.deleteLater` / `thread.deleteLater` → `process_finished` re-enables UI.

## Update Mechanism

Three independent update flows, all triggered from the Help menu:

| Target | API Endpoint | Version Source |
|--------|-------------|---------------|
| sc64deployer | `SummerCart64/releases/latest` | Deployer's `--version` output vs. GitHub tag |
| sc64menu.n64 | `N64FlashcartMenu/releases/latest` | Hex-pattern scan of downloaded binary vs. `published_at` date |
| SC64 firmware | `SummerCart64/releases/latest` | `firmware info` output vs. GitHub tag |

Downloads use `requests.get(url, stream=True)` into `tempfile.mkstemp()` files. Archives are extracted with `zipfile` or `tarfile`.

## Platform Handling

Detected at startup via `sys.platform`:

| Platform | Behavior |
|----------|----------|
| Windows | File dialog filters `*.exe`; executable named `sc64deployer.exe` |
| Linux | Prepends `sudo -n` to all commands; no file extension filter |
| macOS | Same as Linux minus `sudo` |

## Settings Persistence

Uses `QSettings("SC64 deployer Gui", "Settings")`:

- `MainWindow/exe_path` — last selected deployer path (restored on startup)
- `MainWindow/size` — window dimensions

## Known Issues and Technical Debt

### Python method "overloading"

`enable_run_button` and `run_command` are each defined twice with different signatures. Python does not support method overloading — the second definition silently replaces the first. The single-argument versions are dead code.

### Bare except clauses

Several `try/except:` blocks catch all exceptions without logging or re-raising, which can hide bugs during update checks and firmware operations.

### Temp file cleanup

`download_zip()` and the firmware update flow create temp files via `tempfile.mkstemp()` that are not always deleted after use.

### tarfile path traversal

`extract_zip()` calls `tarfile.extractall()` without path validation, which is vulnerable to directory traversal attacks (CVE-2007-4559). Use `filter='data'` on Python 3.12+ or validate member paths.

### Monolithic widget

`SC64MainWidget` handles UI, networking, binary parsing, file I/O, and process management. Extracting an `UpdateManager` and a `CommandBuilder` would improve testability and readability.

### sc64menu version detection

The hex-pattern scanning in `do_next_thing()` uses nested hard-coded patterns with `if`/`else` chains — fragile across sc64menu releases.

### Signal connection accumulation

`enable_run_button` disconnects and reconnects `run_command_button.clicked` each time, which is correct but relies on checking `receivers()` count first. A missed disconnect path would cause duplicate firings.
