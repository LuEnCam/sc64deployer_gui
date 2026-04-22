# SD Card Explorer - Developer Implementation Guide

## Overview

This guide explains how to parse the `sd ls` command output and populate the file tree with real SD card contents.

## Current Status

The SD Explorer is fully functional with:
- ✅ UI framework complete
- ✅ Drag & drop support
- ✅ Rename functionality
- ✅ Delete functionality
- ✅ Upload/Download operations
- ⏳ File listing shows placeholder data (needs output parsing)

## Implementation Task: Parse `sd ls` Output

### Current Code Location

**File**: `sd_explorer.py`, **Method**: `_populate_tree()`

```python
def _populate_tree(self):
    """Populate the file tree widget (simplified for demo)"""
    self.file_tree_widget.clear()
    
    # TODO: Parse actual output from sd ls command
    # Currently shows placeholder data
    example_items = [
        ("roms", "folder", "-"),
        ("saves", "folder", "-"),
        ("game.z64", "file", "8.5 MB"),
    ]
```

### Step 1: Understand the sc64deployer Output Format

First, determine what `sd ls` actually outputs. Based on common file listing tools:

```bash
sc64deployer sd ls /
# Expected output format (TBD - need to verify):
# drwxr-xr-x    folder  /roms
# drwxr-xr-x    folder  /saves
# -rw-r--r--  8.5 MB   game.z64
```

**Action**: Run `sc64deployer sd ls /` and capture actual output format.

### Step 2: Create Output Parser

Add a parsing method to `SDCardExplorer`:

```python
def _parse_ls_output(self, output: str) -> List[tuple]:
    """
    Parse sd ls command output into file items.
    
    Returns:
        List of tuples: (name, type, size)
        - name: str - filename/foldername
        - type: str - "file" or "folder"
        - size: str - human-readable size or "-" for folders
    """
    items = []
    
    # Split output into lines
    lines = output.strip().split('\n')
    
    for line in lines:
        if not line.strip():
            continue
        
        # Parse line based on actual format
        # Example parsing (adjust based on actual format):
        parts = line.split()
        
        if len(parts) >= 3:
            # parts[0] could be permissions (e.g., "drwxr-xr-x")
            # parts[1] could be size or type
            # parts[2] could be name
            
            is_dir = line.startswith('d')  # Unix convention
            name = parts[-1]  # Last part is usually the name
            size = parts[1] if len(parts) > 2 else "-"
            
            items.append((
                name,
                "folder" if is_dir else "file",
                size
            ))
    
    return items
```

### Step 3: Capture Output from Worker

Modify `SDOperationWorker` to collect and return full output:

**Current Code** (`sd_explorer.py`, `SDOperationWorker.run()`):

```python
def run(self):
    # ... existing code ...
    output_lines = []
    
    # Read stdout and collect lines
    for line in self._process.stdout:
        line_stripped = line.strip()
        output_lines.append(line_stripped)
        self.output.emit(line_stripped)  # Keep existing signal
    
    # Store collected output
    self.full_output = '\n'.join(output_lines)
    
    # ... rest of code ...
```

### Step 4: Update _on_list_complete to Parse Output

**Current Code** (`sd_explorer.py`, `_on_list_complete()`):

```python
def _on_list_complete(self):
    """Handle completion of list operation"""
    self.progress_bar.setVisible(False)
    
    # Get full output from worker
    if hasattr(self.worker, 'full_output'):
        items = self._parse_ls_output(self.worker.full_output)
        self.file_tree_widget.clear()
        
        # Handle parent directory
        if self.current_path != "/":
            parent_item = QTreeWidgetItem(["..", "folder", "-"])
            parent_item.setData(0, Qt.ItemDataRole.UserRole, "..")
            self.file_tree_widget.addTopLevelItem(parent_item)
        
        # Add parsed items
        for name, ftype, size in items:
            item = QTreeWidgetItem([name, ftype, size])
            item.setData(0, Qt.ItemDataRole.UserRole, name)
            self.file_tree_widget.addTopLevelItem(item)
    
    self.status_changed.emit(f"Loaded: {self.current_path}")
```

### Step 5: Handle Different Output Formats

Different systems may output different formats. Create flexible parser:

```python
def _parse_ls_output(self, output: str) -> List[tuple]:
    """Robust parser for different ls output formats"""
    items = []
    
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Try to detect format and parse accordingly
        parsed = self._try_parse_unix_format(line) or \
                 self._try_parse_windows_format(line) or \
                 self._try_parse_simple_format(line)
        
        if parsed:
            items.append(parsed)
    
    return items

def _try_parse_unix_format(self, line: str) -> Optional[tuple]:
    """Parse Unix-style output: drwxr-xr-x ... name"""
    if len(line) < 10:
        return None
    
    is_dir = line[0] == 'd'
    parts = line.split()
    
    if len(parts) < 9:
        return None
    
    # Typically: perms links owner group size month day time/year name
    name = ' '.join(parts[8:])  # Handle names with spaces
    size = parts[4] if not is_dir else "-"
    
    return (name, "folder" if is_dir else "file", size)

def _try_parse_windows_format(self, line: str) -> Optional[tuple]:
    """Parse Windows-style output: MM/DD/YYYY HH:MM <DIR|size> name"""
    # Implementation depends on actual Windows format
    pass

def _try_parse_simple_format(self, line: str) -> Optional[tuple]:
    """Fallback for simple format: just filename and optional size"""
    parts = line.split()
    if len(parts) >= 1:
        name = parts[0]
        size = parts[1] if len(parts) > 1 else "-"
        is_dir = name.endswith('/')
        return (name.rstrip('/'), "folder" if is_dir else "file", size)
    return None
```

### Step 6: Add Size Formatting Helper

```python
def _format_size(self, size_str: str) -> str:
    """Convert size string to human-readable format"""
    try:
        size_bytes = int(size_str)
        
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    except (ValueError, TypeError):
        return size_str  # Return as-is if can't parse
```

### Step 7: Add Unit Tests

Create `test_sd_explorer.py`:

```python
import unittest
from sd_explorer import SDCardExplorer

class TestSDLsParsing(unittest.TestCase):
    
    def setUp(self):
        # Mock explorer
        self.explorer = SDCardExplorer.__new__(SDCardExplorer)
    
    def test_parse_unix_format(self):
        """Test Unix-style ls output parsing"""
        output = """drwxr-xr-x    4096 roms
-rw-r--r--    8589934592 game.z64
drwxr-xr-x    4096 saves"""
        
        items = self.explorer._parse_ls_output(output)
        
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0][0], "roms")
        self.assertEqual(items[0][1], "folder")
        self.assertEqual(items[1][0], "game.z64")
        self.assertEqual(items[1][1], "file")
    
    def test_empty_output(self):
        """Test empty directory"""
        items = self.explorer._parse_ls_output("")
        self.assertEqual(len(items), 0)
    
    def test_format_size(self):
        """Test size formatting"""
        self.assertEqual(self.explorer._format_size("1024"), "1.0 KB")
        self.assertEqual(self.explorer._format_size("1048576"), "1.0 MB")
```

### Step 8: Collect Actual Output Format

**Next Action for Developer:**

1. Connect your SC64 device
2. Run this command manually:
   ```bash
   sc64deployer sd ls /
   sc64deployer sd ls /roms  # or other directories
   ```
3. Capture the exact output format
4. Update parsing logic based on actual format
5. Test with various directory structures

### Step 9: Enhanced Tree Display

Add file type detection and icons:

```python
def _get_icon_for_file(self, filename: str, is_dir: bool):
    """Get appropriate icon based on file type"""
    if is_dir:
        return self._get_folder_icon()
    
    ext = Path(filename).suffix.lower()
    
    icons = {
        '.z64': 'rom',
        '.n64': 'rom',
        '.v64': 'rom',
        '.bin': 'binary',
        '.ndd': 'disk',
        '.sra': 'save',
        '.eep': 'eeprom',
        '.txt': 'text',
        '.dat': 'database',
    }
    
    return self._get_file_icon(icons.get(ext, 'generic'))
```

### Step 10: Add Recursive Directory Listing (Optional)

For total size calculation:

```python
def _get_total_size(self, path: str) -> int:
    """Recursively calculate directory size"""
    # Would require additional sd stat calls
    # or parsing 'du' style output if available
    pass
```

## Testing Checklist

- [ ] Parser handles empty directories
- [ ] Parser handles file names with spaces
- [ ] Parser handles deeply nested directories
- [ ] Size formatting works for all magnitudes
- [ ] Parent directory (".." ) works correctly
- [ ] Refresh works after operations
- [ ] Large directories don't hang UI
- [ ] Different file extensions show correctly

## Performance Considerations

1. **Large directories**: Consider pagination or lazy loading
2. **Network latency**: Implement timeout handling
3. **Long path names**: Ellipsis truncation in tree display
4. **Frequent updates**: Debounce refresh requests

## References

- Python `pathlib`: https://docs.python.org/3/library/pathlib.html
- PyQt6 QTreeWidget: https://www.riverbankcomputing.com/software/pyqt/intro
- File size formats: https://en.wikipedia.org/wiki/Byte#Multiple-byte_units

---

**Priority**: Implement output parsing in the order listed above.  
**Estimated Time**: 2-4 hours for complete implementation.
