# SD Card Explorer Refactor - Documentation

## Overview

The SD card operations have been refactored from a command-based interface to a modern **file explorer widget** that provides a more intuitive user experience similar to Windows Explorer or Finder.

## What Changed

### Previous Interface (Still Available)
- Command-based buttons: `sd ls`, `sd upload`, `sd download`, etc.
- Manual path input via text fields
- Sequential command execution
- Located in the "Commands" tab

### New SD Card Explorer Interface
- **Visual file tree widget** displaying SD card contents
- **Drag & drop support** for uploading files
- **Inline rename** for files and directories
- **Right-click context menu** for common operations
- **Automatic refresh** after operations
- **Progress feedback** during file transfers
- Located in the "SD Card Explorer" tab (auto-enabled when deployer is selected)

## File Structure

```
sc64deployer_gui/
├── main.py                          # Main application (updated with tab UI)
├── exec_runner.py                   # Background worker for subprocess execution
├── sd_explorer.py                   # NEW: SD Card Explorer widget
├── sc64_lists_command_options.py     # Command definitions
└── ... (other files)
```

## Key Features

### 1. **File Tree Navigation**
- Browse SD card directory structure
- Double-click folders to navigate into them
- Click ".." to go to parent directory
- Manual path entry via "Navigate to path" field

### 2. **File Operations**

#### Download (SD → PC)
1. Select file in the tree
2. Click "Download" button or right-click → "Download"
3. Choose save location on your PC
4. File is transferred automatically

#### Upload (PC → SD)
**Method 1: Dialog**
1. Click "Upload File" button
2. Select file from your PC
3. File uploads to current SD directory

**Method 2: Drag & Drop**
1. Drag files from File Explorer / Finder
2. Drop onto the SD Explorer tree widget
3. Files upload automatically to current directory

#### Rename
1. Select file/folder in the tree
2. Click "Rename" button or right-click → "Rename"
3. Enter new name in dialog
4. Confirm to apply change

#### Delete
1. Select file/folder in the tree
2. Click "Delete" button or right-click → "Delete"
3. Confirm deletion (no undo!)
4. File/folder removed from SD card

#### Create Folder
1. Click "New Folder" button
2. Note: Folder creation depends on sc64deployer capabilities
3. Current limitation: May not be fully supported

### 3. **Status & Feedback**
- Real-time status messages below file tree
- Progress bar during operations
- Operation completion notifications
- Error handling with user-friendly messages

## Architecture

### `SDCardExplorer` Widget (`sd_explorer.py`)
Main UI component containing:
- `QTreeWidget` for file display
- Navigation bar with path input
- Operation buttons (download, upload, rename, delete, etc.)
- Progress bar and status label
- Context menu support

### `SDOperationWorker` Class (`sd_explorer.py`)
Background worker thread for:
- Executing `sd ls`, `sd download`, `sd upload`, `sd mv`, `sd rm` commands
- Handling subprocess communication
- Emitting signals for status updates and errors

### Integration in `SC64MainWidget` (`main.py`)
- Creates tab widget with two tabs: "Commands" and "SD Card Explorer"
- SD Explorer tab auto-enabled when deployer executable is selected
- Handles exe path updates and passes them to SD Explorer

## Usage Workflow

### First Time Setup
1. **Launch application**
2. **File → Select sc64deployer** (select the deployer executable)
3. Both tabs become enabled
4. Application settings are saved automatically

### Using SD Card Explorer
1. **Click "SD Card Explorer" tab**
2. **Navigate** to desired directory (or stay at root "/")
3. **Perform operations:**
   - Download files: Select file → Click "Download"
   - Upload files: Click "Upload File" or drag & drop
   - Rename: Select item → Click "Rename"
   - Delete: Select item → Click "Delete"
4. **Status bar** shows operation results
5. **File tree** auto-refreshes after each operation

## Technical Details

### Threading Model
- All SD card operations run in background `QThread`
- UI remains responsive during file transfers
- Only one operation at a time (enforced by worker)
- Signals (`pyqtSignal`) communicate between threads

### Command Mapping
| Explorer Action | SC64 Command | Arguments |
|---|---|---|
| Refresh/Navigate | `sd ls` | `<PATH>` |
| Download | `sd download` | `<SD_PATH> <PC_PATH>` |
| Upload | `sd upload` | `<PC_PATH> <SD_PATH>` |
| Rename | `sd mv` | `<OLD_PATH> <NEW_PATH>` |
| Delete | `sd rm` | `<PATH>` |

### Error Handling
- Subprocess errors caught and displayed to user
- Non-zero exit codes reported
- Invalid paths handled gracefully
- Thread cleanup ensures no resource leaks

## Platform Support

Runs on all supported platforms:
- **Windows**: Native file paths, `.exe` deployer
- **Linux**: Uses `sudo -n` for elevated access, Linux binary deployer
- **macOS**: Same as Linux minus `sudo`

## Known Limitations & Future Enhancements

### Current Limitations
1. **Folder creation** (`mkdir`) may not be fully supported by sc64deployer
2. **File properties** (size, date) require additional parsing of `ls` output
3. **Large file transfers** show indeterminate progress (no percentage)
4. **Drag & drop** only works for uploading (not reordering in tree)

### Potential Enhancements
1. Parse `stat` output for detailed file metadata
2. Implement batch upload/download operations
3. Add file type icons for visual differentiation
4. Implement recursive folder deletion
5. Add file size calculations
6. Add upload queue management
7. Add favorites/bookmarks for common directories
8. Implement file search functionality
9. Add detailed transfer statistics and speed monitoring
10. Add preview capability for text files

## Backward Compatibility

- **Original command interface still available** in "Commands" tab
- **Both tabs coexist** without interference
- **Settings preserved** (exe path, window size)
- **No breaking changes** to existing code (except UI layout)

## Migration Guide for Developers

### If you want to extend the SD Explorer:

#### Add a new operation button:
```python
# In SDCardExplorer._init_ui()
self.new_operation_btn = QPushButton("New Operation")
self.new_operation_btn.clicked.connect(self._new_operation)
button_layout.addWidget(self.new_operation_btn)

# Add the handler method
def _new_operation(self):
    # Implement operation logic
    self._execute_sd_operation(
        "operation_name",
        [shlex.quote(path1), shlex.quote(path2)],
        "Operation completed successfully"
    )
```

#### Update the file tree display:
```python
# Enhance _populate_tree() method
# Parse the output from `sd ls` to extract:
# - File names
# - File types (directory vs file)
# - File sizes
# - Modification dates (if available)
```

#### Add keyboard shortcuts:
```python
# In SDCardExplorer._init_ui()
self.file_tree_widget.keyPressEvent = self._on_tree_key_press

def _on_tree_key_press(self, event):
    if event.key() == Qt.Key.Key_Delete:
        self._delete_file()
    elif event.key() == Qt.Key.Key_F5:
        self._refresh_sd_contents()
    # ... handle other keys
```

## Troubleshooting

### SD Explorer tab is grayed out
- **Cause**: No deployer selected
- **Solution**: File → Select sc64deployer

### File operations fail with "Command failed" error
- **Cause**: Invalid path, permission issues, or device disconnected
- **Solution**: Check device connection, verify path, check console output

### Drag & drop not working
- **Cause**: Platform-specific Qt issue
- **Solution**: Use "Upload File" button as alternative

### Explorer not showing files
- **Cause**: SD card may have unusual filesystem format
- **Solution**: Try navigating with manual path entry

## References

- PyQt6 Documentation: https://www.riverbankcomputing.com/software/pyqt/
- sc64deployer Commands: See `sc64_lists_command_options.py`
- Architecture Overview: See `ARCHITECTURE.md`
