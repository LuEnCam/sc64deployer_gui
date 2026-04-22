# SD Card Explorer - Architecture & System Design

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Main Application (main.py)                  │
│  SC64MainWindow - Creates QMainWindow, Menu Bar, Status Bar     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
            ┌────────────────────────────────────┐
            │    SC64MainWidget (QWidget)        │
            │  - File menu (Select deployer)     │
            │  - Help menu (Updates)             │
            │  - Status bar (exe_path display)   │
            └────────────────┬───────────────────┘
                             │
                             ▼
            ┌──────────────────────────────────────┐
            │     QTabWidget (Tab Container)       │
            │  ┌─────────────┬────────────────────┐│
            │  │   Tab 1     │      Tab 2         ││
            │  │ "Commands"  │ "SD Card Explorer" ││
            │  └─────────────┴────────────────────┘│
            └────────────────┬─────────────────────┘
           /                 │                    \
          /                  │                     \
         ▼                   ▼                      ▼
    ┌──────────┐      ┌─────────────────┐        [placeholder]
    │ Original │      │ SDCardExplorer  │
    │ Commands │      │  (sd_explorer)  │
    │ Interface│      │                 │
    └──────────┘      │ ┌─────────────┐ │
                      │ │ QTreeWidget │ │
                      │ ├─────────────┤ │
                      │ │ Path Input  │ │
                      │ │ Buttons     │ │
                      │ │ Progress Bar│ │
                      │ │ Status Label│ │
                      │ └─────────────┘ │
                      │                 │
                      │   ┌─────────────┴──────────────┐
                      │   │ Background Operations      │
                      │   │ (QThread + Worker)         │
                      │   └────────────┬───────────────┘
                      └────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
              ┌──────────────┐    ┌───────────┐    ┌─────────┐
              │ Subprocess   │    │ sc64      │    │   SD    │
              │ Execution    │    │ deployer  │────│ Device  │
              │ (exec_runner)│    │ Binary    │    │  (USB)  │
              └──────────────┘    └───────────┘    └─────────┘
```

## Component Interactions

### 1. **User Selects Deployer**
```
User clicks "Select sc64deployer"
    ↓
File dialog opens
    ↓
User selects exe_path
    ↓
check_set_exe() called
    ↓
_init_sd_explorer() called
    ↓
SDCardExplorer tab enabled
    ↓
SD Explorer ready to use
```

### 2. **User Lists SD Card Contents**
```
User clicks "Refresh" or enters folder
    ↓
_refresh_sd_contents() called
    ↓
SDOperationWorker created on QThread
    ↓
Worker executes: sc64deployer sd ls <PATH>
    ↓
stdout captured → parsed → items created
    ↓
_on_list_complete() processes items
    ↓
QTreeWidget populated with results
    ↓
UI updated (non-blocking)
```

### 3. **User Downloads File**
```
User selects file in tree
    ↓
User clicks "Download"
    ↓
Save dialog opens
    ↓
_download_file() called
    ↓
_execute_sd_operation("download", ...) called
    ↓
New worker thread starts
    ↓
Worker: sc64deployer sd download <SD_PATH> <PC_PATH>
    ↓
Progress bar shows (indeterminate)
    ↓
Operation completes
    ↓
Tree refreshes automatically
    ↓
Status message shows result
```

### 4. **User Uploads File (Drag & Drop)**
```
User drags file from File Explorer
    ↓
Drop on tree widget
    ↓
_drop_event() triggered
    ↓
_upload_file_from_pc_path() called
    ↓
_execute_sd_operation("upload", ...) called
    ↓
Worker: sc64deployer sd upload <PC_PATH> <SD_PATH>
    ↓
[Same as download process...]
```

## Data Flow Diagram

### File Listing Pipeline
```
sc64deployer output
        ↓
    [raw text]
        ↓
  SDOperationWorker.run()
        ↓
  [capture stdout/stderr]
        ↓
  _parse_ls_output()  ← NEEDS IMPLEMENTATION
        ↓
  [(name, type, size) tuples]
        ↓
  QTreeWidgetItem creation
        ↓
  QTreeWidget display
```

### Command Execution Pipeline
```
User action (button click)
        ↓
  _execute_sd_operation()
        ↓
  Create SDOperationWorker
        ↓
  Move to QThread
        ↓
  Start thread
        ↓
  Worker.run() (background)
        ↓
  subprocess.Popen()
        ↓
  Execute: sc64deployer sd <cmd> <args>
        ↓
  Capture output/errors
        ↓
  finished signal emitted
        ↓
  Thread cleanup
        ↓
  _on_operation_complete()
        ↓
  Refresh tree
        ↓
  Update UI with status
```

## Class Hierarchy

```
QWidget
  ├─ SC64MainWidget
  │   └─ Uses: QTabWidget, QGridLayout, SDCardExplorer
  │
  └─ SDCardExplorer (QWidget)
      ├─ QTreeWidget (displays files)
      ├─ QLineEdit (path navigation)
      ├─ QPushButton (operation buttons)
      ├─ QProgressBar (operation progress)
      ├─ QLabel (status display)
      └─ Uses: SDOperationWorker, QThread

QObject
  ├─ ExecWorker (background operation)
  │   └─ Used by: SC64MainWidget (for non-SD commands)
  │
  └─ SDOperationWorker (background operation)
      └─ Used by: SDCardExplorer (for SD operations)
```

## Signal & Slot Connections

### SDCardExplorer Signals

```
operation_completed
    → Emitted when: Any SD operation finishes
    → Connected to: Auto-refresh trigger
    → Causes: _refresh_sd_contents()

status_changed(str)
    → Emitted when: Operation starts/completes
    → Connected to: status_label.setText()
    → Causes: Status update in UI
```

### Worker Signals (SDOperationWorker)

```
output(str)
    → Emitted for: Each stdout line
    → Connects to: Data collection

error(str)
    → Emitted when: Errors occur
    → Connects to: Error display

finished()
    → Emitted when: Process completes
    → Triggers: Cleanup + refresh
```

## Thread Management

```
Main UI Thread (QThread)
    │
    ├─→ User clicks button
    │
    └─→ _execute_sd_operation() called
            │
            ├─→ Create Worker
            ├─→ Create QThread
            ├─→ moveToThread()
            │
            └─→ Start thread
                    │
                    ▼
            Worker Thread
                    │
                    ├─→ subprocess.Popen()
                    ├─→ Read stdout/stderr
                    ├─→ Emit signals
                    │
                    └─→ finished signal
                            │
                            ▼
                    Main Thread (slot)
                            │
                            ├─→ thread.quit()
                            ├─→ worker.deleteLater()
                            ├─→ _refresh_sd_contents()
                            │
                            └─→ UI updated
```

## Configuration & State

### Persistent State (QSettings)
```
MainWindow/
    ├─ exe_path      → sc64deployer executable path
    └─ size          → Window dimensions
```

### Runtime State
```
SDCardExplorer
    ├─ exe_path          → Deployer path
    ├─ current_path      → Current SD directory (e.g., "/roms")
    ├─ file_tree         → Directory structure cache
    ├─ pc_pending_upload → Drag & drop file tracking
    ├─ worker_thread     → Active operation thread
    └─ worker            → Active operation worker
```

## Error Handling Flow

```
Operation fails
    ↓
worker.error signal emitted
    ↓
error message captured
    ↓
Status: "Operation failed: <message>"
    ↓
User sees error in status bar
    ↓
Tree does NOT refresh (preserves previous state)
    ↓
User can retry
```

## Platform-Specific Behavior

### Windows
```
exe_path: .exe file
Command: sc64deployer sd ls /
No sudo elevation
```

### Linux
```
exe_path: Binary executable
Command: sudo -n sc64deployer sd ls /
Auto-elevation with PolicyKit
```

### macOS
```
exe_path: Binary executable
Command: sc64deployer sd ls /
Same as Linux, no sudo
```

## File Operation Mapping

```
Explorer Action          SC64 Command           Arguments
─────────────────────    ─────────────────      ──────────────────
Refresh/Navigate         sd ls                  <PATH>
Download                 sd download            <SRC_SD> <DEST_PC>
Upload                   sd upload              <SRC_PC> <DEST_SD>
Rename                   sd mv                  <OLD_PATH> <NEW_PATH>
Delete                   sd rm                  <PATH>
New Folder               sd mkdir               <PATH>* (not always supported)
Show Properties          sd stat                <PATH>* (data not displayed yet)
```

## Performance Characteristics

| Operation | Typical Time | Blocking | Notes |
|-----------|---|---|---|
| Refresh directory | 500ms - 2s | No | Depends on file count |
| Download small file | 1-5s | No | Depends on file size |
| Upload small file | 1-5s | No | Depends on USB speed |
| Rename file | 500ms | No | Usually fast |
| Delete file | 200-500ms | No | Immediate removal |

## Resource Management

```
Memory
├─ UI widgets:        Constant (~5-10 MB)
├─ File tree items:   Per item (~100 bytes)
├─ Background thread: Only when operating
└─ Worker process:    Only while running

Threads
├─ Main UI thread:    Always active
├─ File operation:    Created per operation
└─ Max concurrent:    1 (enforced)

File Handles
├─ Subprocess stdin:  Opened during operation
├─ Subprocess stdout: Opened during operation
└─ Subprocess stderr: Opened during operation
```

## Extensibility Points

### Adding New Operations

```python
# 1. Add button in _init_ui()
self.new_op_btn = QPushButton("New Operation")
self.new_op_btn.clicked.connect(self._new_operation)

# 2. Add handler method
def _new_operation(self):
    self._execute_sd_operation(
        "operation_name",
        [shlex.quote(arg1), shlex.quote(arg2)],
        "Success message"
    )
```

### Adding New File Types/Icons

```python
# In _get_icon_for_file()
ext_icons = {
    '.new_ext': 'custom_icon_name',
    ...
}
```

### Custom Status Handlers

```python
# Connect to status signal
self.sd_explorer.status_changed.connect(
    lambda msg: self.on_sd_status(msg)
)
```

## Security Model

```
Input Validation
├─ Paths quoted with shlex.quote()
├─ No string interpolation in commands
├─ Arguments passed as list (not string)
└─ Shell injection prevented

Process Isolation
├─ subprocess.Popen() isolates process
├─ No shell=True (blocks command injection)
├─ stdin/stdout/stderr piped (captured)
└─ Process can be terminated

Permission Model
├─ Linux: sudo -n (non-interactive)
├─ User must pre-authorize with sudoers config
├─ No hardcoded passwords
└─ Respects system permissions
```

---

## Key Design Decisions

1. **Tab-based UI**: Keeps old and new interfaces separate
2. **Background threading**: All operations non-blocking
3. **Single operation at a time**: Simplifies state management
4. **QTreeWidget**: Efficient for large file lists
5. **Signal/slot architecture**: Thread-safe communication
6. **shlex.quote()**: Security for path handling

---

For more details, see:
- `SD_EXPLORER_REFACTOR.md` - Feature documentation
- `SD_EXPLORER_IMPLEMENTATION.md` - Implementation guide
- Code comments in `sd_explorer.py` - Inline documentation
