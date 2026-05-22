# sd_explorer.py - SD Card File Explorer Widget

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
    QPushButton, QLineEdit, QLabel, QMessageBox, QInputDialog, QFileDialog,
    QMenu, QAbstractItemView, QProgressBar, QHeaderView, QProgressDialog, QApplication
)
from PyQt6.QtGui import QIcon, QDrag, QFont, QColor, QBrush
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QUrl, QMimeData as QMimeDataCore
from PyQt6.QtCore import QObject
import subprocess
import sys
import shlex
import os
import tempfile
import time
from enum import Enum
from pathlib import Path
from typing import Optional, List, Callable


class SDOperationType(Enum):
    LIST = "list"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    RENAME = "rename"
    DELETE = "delete"
    MKDIR = "mkdir"


class SDOperationWorker(QObject):
    """Background worker for SD card operations"""
    output = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, exe_path: str, command: str, options: List[str] = None):
        super().__init__()
        self.exe_path = exe_path
        self.command = command
        self.options = options or []
        self._process = None

    def run(self):
        try:
            cmd = []
            if sys.platform.startswith("linux"):
                cmd = ['sudo', '-n']

            cmd.extend([self.exe_path, "sd", self.command])
            cmd.extend(self.options)

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Read stdout
            for line in self._process.stdout:
                self.output.emit(line.strip())
            self._process.stdout.close()

            # Read stderr
            err = self._process.stderr.read()
            if err:
                self.error.emit(err.strip())
            self._process.stderr.close()

            self._process.wait()
            if self._process.returncode != 0:
                self.error.emit(f"Command failed with exit code {self._process.returncode}")

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def terminate(self):
        if self._process:
            self._process.terminate()


class SDFileItem:
    """Represents a file/directory on the SD card"""
    def __init__(self, name: str, path: str, is_dir: bool, size: int = 0):
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.size = size
        self.children = []

    def __repr__(self):
        return f"SDFileItem({self.name}, dir={self.is_dir}, size={self.size})"


class SDCardExplorer(QWidget):
    """File explorer widget for SC64 SD card operations"""
    
    operation_completed = pyqtSignal()
    status_changed = pyqtSignal(str)

    def __init__(self, exe_path: str):
        super().__init__()
        self.exe_path = exe_path
        self.current_path = "/"
        self.file_tree = {}
        self.worker_thread = None
        self.worker = None
        self.pc_pending_upload = None  # Track PC file pending upload via drag & drop
        self.current_listing = []  # Store parsed SD card file listing

        self._init_ui()
        self._refresh_sd_contents()

    def _init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout()

        # Top navigation bar
        nav_layout = QHBoxLayout()
        self.path_label = QLabel(f"Current Path: {self.current_path}")
        self.path_label.setFont(QFont("Courier", 10))
        nav_layout.addWidget(self.path_label)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Navigate to path (e.g., /roms, /)")
        self.path_input.returnPressed.connect(self._navigate_to_path)
        nav_layout.addWidget(self.path_input)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_sd_contents)
        nav_layout.addWidget(self.refresh_btn)

        layout.addLayout(nav_layout)

        # File tree widget
        self.file_tree_widget = QTreeWidget()
        self.file_tree_widget.setColumnCount(3)
        self.file_tree_widget.setHeaderLabels(["Name", "Type", "Size"])
        self.file_tree_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.file_tree_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.file_tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.file_tree_widget.setAcceptDrops(True)
        self.file_tree_widget.setDragEnabled(True)
        self.file_tree_widget.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.file_tree_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.file_tree_widget.dragEnterEvent = self._drag_enter_event
        self.file_tree_widget.dragMoveEvent = self._drag_move_event
        self.file_tree_widget.dropEvent = self._drop_event
        self.file_tree_widget.startDrag = self._start_drag

        # Resize columns
        header = self.file_tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.file_tree_widget)

        # Control buttons
        button_layout = QHBoxLayout()

        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self._download_file)
        button_layout.addWidget(self.download_btn)

        self.upload_btn = QPushButton("Upload File")
        self.upload_btn.clicked.connect(self._upload_file_dialog)
        button_layout.addWidget(self.upload_btn)

        self.rename_btn = QPushButton("Rename")
        self.rename_btn.clicked.connect(self._rename_file)
        button_layout.addWidget(self.rename_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_file)
        button_layout.addWidget(self.delete_btn)

        layout.addLayout(button_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def _cleanup_previous_worker(self):
        """Wait for any previous worker thread to finish before starting a new one."""
        if self.worker_thread is not None:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None

    def _refresh_sd_contents(self):
        """Refresh the file tree from the SD card"""
        self._cleanup_previous_worker()
        self.status_changed.emit("Loading SD card contents...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.current_listing = []  # Clear previous listing

        self.worker_thread = QThread()
        self.worker = SDOperationWorker(self.exe_path, "ls", [self.current_path])
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.output.connect(self._parse_ls_output)  # Connect output signal to parser
        self.worker.finished.connect(lambda: self._on_list_complete())
        self.worker.finished.connect(self.worker_thread.quit)

        self.worker_thread.start()

    def _parse_ls_output(self, line: str):
        """Parse a single line from ls command output.
        
        Format: d/f  SIZE  DATE TIME | /path/name
        Examples:
            d ---- 2025-01-23 10:49:36 | /.fseventsd
            f 8.0M 1996-12-24 23:32:00 | AI Shougi 3 (Japan).n64
        """
        line = line.strip()
        if not line:
            return

        # Split on the '|' separator
        if '|' not in line:
            return
        meta, _, filepath = line.partition('|')
        meta = meta.strip()
        filepath = filepath.strip()

        if not meta or not filepath:
            return

        # First token is type: 'd' or 'f'
        parts = meta.split()
        if len(parts) < 2:
            return

        entry_type = parts[0]
        is_dir = (entry_type == 'd')
        size_str = parts[1]  # e.g. '----', '8.0M', '103K', '0B'

        # Parse size string to bytes
        size = self._parse_size_string(size_str)

        # Extract name from the path (last component)
        name = filepath.rsplit('/', 1)[-1] if '/' in filepath else filepath

        self.current_listing.append({
            'name': name,
            'path': filepath,
            'is_dir': is_dir,
            'size': size
        })

    def _parse_size_string(self, s: str) -> int:
        """Convert a human-readable size string (e.g. '8.0M', '103K', '0B') to bytes."""
        if s == '----':
            return 0
        multipliers = {'B': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
        for suffix, mult in multipliers.items():
            if s.endswith(suffix):
                try:
                    return int(float(s[:-1]) * mult)
                except ValueError:
                    return 0
        try:
            return int(s)
        except ValueError:
            return 0

    def _on_list_complete(self):
        """Handle completion of list operation"""
        self.progress_bar.setVisible(False)
        self._populate_tree()
        self.status_changed.emit(f"Loaded: {self.current_path}")

    def _populate_tree(self):
        """Populate the file tree widget (simplified for demo)"""
        self.file_tree_widget.clear()

        # Navigate up option (if not root)
        if self.current_path != "/":
            parent_item = QTreeWidgetItem(["..", "folder", "-"])
            parent_item.setData(0, Qt.ItemDataRole.UserRole, "..")
            parent_item.setIcon(0, self._get_icon("folder"))
            self.file_tree_widget.addTopLevelItem(parent_item)

        for entry in self.current_listing:
            ftype = "folder" if entry['is_dir'] else "file"
            size = "-" if entry['is_dir'] else self._format_size(entry['size'])
            item = QTreeWidgetItem([entry['name'], ftype, size])
            item.setData(0, Qt.ItemDataRole.UserRole, entry['name'])
            icon = self._get_icon(ftype)
            item.setIcon(0, icon)
            self.file_tree_widget.addTopLevelItem(item)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click to navigate into directory"""
        name = item.text(0)
        ftype = item.text(1)

        if name == "..":
            # Navigate to parent
            parts = self.current_path.rstrip("/").split("/")
            if len(parts) > 1:
                self.current_path = "/".join(parts[:-1]) or "/"
            else:
                self.current_path = "/"
        elif ftype == "folder":
            # Navigate into folder
            if self.current_path.endswith("/"):
                self.current_path += name
            else:
                self.current_path += "/" + name

        self.path_label.setText(f"Current Path: {self.current_path}")
        self.path_input.clear()
        self._refresh_sd_contents()

    def _navigate_to_path(self):
        """Navigate to a custom path"""
        new_path = self.path_input.text().strip()
        if new_path:
            self.current_path = new_path
            self.path_label.setText(f"Current Path: {self.current_path}")
            self._refresh_sd_contents()

    def _show_context_menu(self, position):
        """Show context menu on right-click"""
        item = self.file_tree_widget.itemAt(position)
        if not item:
            return

        menu = QMenu()
        download_action = menu.addAction("Download")
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")

        action = menu.exec(self.file_tree_widget.mapToGlobal(position))

        if action == download_action:
            self._download_file()
        elif action == rename_action:
            self._rename_file()
        elif action == delete_action:
            self._delete_file()

    def _download_file(self):
        """Download selected file from SD card"""
        item = self.file_tree_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a file to download.")
            return

        filename = item.text(0)
        ftype = item.text(1)

        if ftype == "folder":
            QMessageBox.warning(self, "Invalid Selection", "Cannot download folders.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save File As", filename, "All Files (*.*)"
        )

        if save_path:
            self._execute_sd_operation(
                "download",
                [f"{self.current_path.rstrip('/')}/{filename}",
                 save_path],
                f"Downloaded: {filename}"
            )

    def _upload_file_dialog(self):
        """Upload a file to SD card"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File to Upload", "", "All Files (*.*)"
        )

        if file_path:
            filename = os.path.basename(file_path)
            dest_path = f"{self.current_path.rstrip('/')}/{filename}"

            self._execute_sd_operation(
                "upload",
                [file_path, dest_path],
                f"Uploaded: {filename}"
            )

    def _upload_file_from_pc_path(self, pc_path: str):
        """Upload a specific file from PC to SD card"""
        filename = os.path.basename(pc_path)
        dest_path = f"{self.current_path.rstrip('/')}/{filename}"

        self._execute_sd_operation(
            "upload",
            [pc_path, dest_path],
            f"Uploaded: {filename}"
        )

    def _rename_file(self):
        """Rename a file or directory"""
        item = self.file_tree_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a file to rename.")
            return

        old_name = item.text(0)
        if old_name == "..":
            return

        new_name, ok = QInputDialog.getText(
            self, "Rename", f"New name for '{old_name}':", text=old_name
        )

        if ok and new_name and new_name != old_name:
            old_path = f"{self.current_path.rstrip('/')}/{old_name}"
            new_path = f"{self.current_path.rstrip('/')}/{new_name}"

            self._execute_sd_operation(
                "mv",
                [old_path, new_path],
                f"Renamed: {old_name} → {new_name}"
            )

    def _delete_file(self):
        """Delete a file or empty directory"""
        item = self.file_tree_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a file to delete.")
            return

        filename = item.text(0)
        if filename == "..":
            return

        reply = QMessageBox.question(
            self, "Confirm Delete", f"Delete '{filename}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            file_path = f"{self.current_path.rstrip('/')}/{filename}"
            self._execute_sd_operation(
                "rm",
                [file_path],
                f"Deleted: {filename}"
            )

    # Custom MIME type for internal SD card drag & drop
    SD_MIME_TYPE = "application/x-sd-card-path"

    def _start_drag(self, supportedActions):
        """Start a drag operation with SD card path info"""
        item = self.file_tree_widget.currentItem()
        if not item or item.text(0) == "..":
            return

        name = item.text(0)
        sd_path = f"{self.current_path.rstrip('/')}/{name}"

        mime_data = QMimeDataCore()
        mime_data.setData(self.SD_MIME_TYPE, sd_path.encode('utf-8'))

        drag = QDrag(self.file_tree_widget)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)

    def _drag_enter_event(self, event):
        """Handle drag enter event for both internal and external drops"""
        if event.mimeData().hasFormat(self.SD_MIME_TYPE) or event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drag_move_event(self, event):
        """Accept drag move events for both internal and external drops"""
        if event.mimeData().hasFormat(self.SD_MIME_TYPE) or event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event):
        """Handle drop: internal SD move or external PC file upload"""
        mime = event.mimeData()

        if mime.hasFormat(self.SD_MIME_TYPE):
            # Internal SD card move
            source_path = bytes(mime.data(self.SD_MIME_TYPE)).decode('utf-8')
            source_name = source_path.rsplit('/', 1)[-1]

            # Determine target folder from the item under the cursor
            target_item = self.file_tree_widget.itemAt(event.position().toPoint())
            if target_item and target_item.text(1) == "folder":
                if target_item.text(0) == "..":
                    # Dropped on ".." → move to parent directory
                    parts = self.current_path.rstrip("/").rsplit("/", 1)
                    target_dir = parts[0] if parts[0] else "/"
                else:
                    target_dir = f"{self.current_path.rstrip('/')}/{target_item.text(0)}"
            else:
                # Dropped on a file or empty space → stay in current directory
                target_dir = self.current_path.rstrip('/')

            dest_path = f"{target_dir}/{source_name}"

            if dest_path == source_path:
                return  # No-op: same location

            reply = QMessageBox.question(
                self, "Move File",
                f"Move '{source_name}' to '{target_dir}/'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._execute_sd_operation(
                    "mv",
                    [source_path, dest_path],
                    f"Moved: {source_name} → {target_dir}/"
                )
            event.acceptProposedAction()

        elif mime.hasUrls():
            # External file drop from OS → upload
            target_item = self.file_tree_widget.itemAt(event.position().toPoint())
            if target_item and target_item.text(1) == "folder" and target_item.text(0) != "..":
                upload_dir = f"{self.current_path.rstrip('/')}/{target_item.text(0)}"
            else:
                upload_dir = self.current_path.rstrip('/')

            for url in mime.urls():
                pc_path = url.toLocalFile()
                if os.path.isfile(pc_path):
                    filename = os.path.basename(pc_path)
                    dest_path = f"{upload_dir}/{filename}"
                    self._execute_sd_operation(
                        "upload",
                        [pc_path, dest_path],
                        f"Uploaded: {filename}"
                    )
            event.acceptProposedAction()

    def _execute_sd_operation(self, operation: str, args: List[str], success_message: str):
        """Execute an SD card operation in a background thread"""
        self._cleanup_previous_worker()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_changed.emit(f"Executing: {operation}...")

        self.worker_thread = QThread()
        self.worker = SDOperationWorker(self.exe_path, operation, args)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(lambda: self._on_operation_complete(success_message))
        self.worker.finished.connect(self.worker_thread.quit)

        self.worker_thread.start()

    def _on_operation_complete(self, message: str):
        """Handle completion of SD operation"""
        self.progress_bar.setVisible(False)
        self.status_changed.emit(message)
        self._refresh_sd_contents()
        self.operation_completed.emit()

    def _get_icon(self, icon_type: str) -> QIcon:
        """Get appropriate icon for file type"""
        # Could be extended to show different icons for different file types
        if icon_type == "folder":
            return QIcon("folder")  # Would use system icons in production
        return QIcon("file")

    def _format_size(self, size: int) -> str:
        """Format byte size to human-readable string"""
        if size <= 0:
            return "0 B"
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
            size /= 1024
        return f"{size:.1f} TB"

    def update_exe_path(self, new_exe_path: str):
        """Update the path to the sc64deployer executable"""
        self.exe_path = new_exe_path
