# sd_explorer.py - SD Card File Explorer Widget

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
    QPushButton, QLineEdit, QLabel, QMessageBox, QInputDialog, QFileDialog,
    QMenu, QAbstractItemView, QProgressBar, QHeaderView
)
from PyQt6.QtGui import QIcon, QDrag, QFont, QColor, QBrush
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QUrl, QMimeData as QMimeDataCore
from PyQt6.QtCore import QObject
import subprocess
import sys
import shlex
import os
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
        self.file_tree_widget.dragEnterEvent = self._drag_enter_event
        self.file_tree_widget.dropEvent = self._drop_event
        
        # Enable drag for items
        self.file_tree_widget.setDragEnabled(True)

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

        self.mkdir_btn = QPushButton("New Folder")
        self.mkdir_btn.clicked.connect(self._create_directory)
        button_layout.addWidget(self.mkdir_btn)

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

    def _refresh_sd_contents(self):
        """Refresh the file tree from the SD card"""
        self.status_changed.emit("Loading SD card contents...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.current_listing = []  # Clear previous listing

        self.worker_thread = QThread()
        self.worker = SDOperationWorker(self.exe_path, "ls", [shlex.quote(self.current_path)])
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.output.connect(self._parse_ls_output)  # Connect output signal to parser
        self.worker.finished.connect(lambda: self._on_list_complete())
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def _parse_ls_output(self, line: str):
        """Parse a single line from ls command output"""
        line = line.strip()
        if not line:
            return
        
        # Parse output format from sc64deployer ls command
        # Expected format: "filename" or filename (directory indicated by trailing /)
        # or with size info: "filename size" for files
        # For now, assume format: name [size] [type_indicator]
        parts = line.split(None, 1)
        if not parts:
            return
        
        name = parts[0].rstrip('/')
        is_dir = line.endswith('/')
        
        # Try to extract size if available
        size = 0
        if len(parts) > 1 and not is_dir:
            try:
                size = int(parts[1].split()[0])
            except (ValueError, IndexError):
                pass
        
        self.current_listing.append({
            'name': name,
            'path': f"{self.current_path.rstrip('/')}/{name}",
            'is_dir': is_dir,
            'size': size
        })

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

        # Add mock entries (would be populated from actual SD listing)
        # This is a simplified version - in production, parse the ls output
        example_items = [
            ("roms", "folder", "-"),
            ("saves", "folder", "-"),
            ("game.z64", "file", "8.5 MB"),
        ]

        for name, ftype, size in example_items:
            item = QTreeWidgetItem([name, ftype, size])
            item.setData(0, Qt.ItemDataRole.UserRole, name)
            icon = self._get_icon("folder" if ftype == "folder" else "file")
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
                [shlex.quote(f"{self.current_path.rstrip('/')}/{filename}"),
                 shlex.quote(save_path)],
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
                [shlex.quote(file_path), shlex.quote(dest_path)],
                f"Uploaded: {filename}"
            )

    def _upload_file_from_pc_path(self, pc_path: str):
        """Upload a specific file from PC to SD card"""
        filename = os.path.basename(pc_path)
        dest_path = f"{self.current_path.rstrip('/')}/{filename}"

        self._execute_sd_operation(
            "upload",
            [shlex.quote(pc_path), shlex.quote(dest_path)],
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
                [shlex.quote(old_path), shlex.quote(new_path)],
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
                [shlex.quote(file_path)],
                f"Deleted: {filename}"
            )

    def _create_directory(self):
        """Create a new directory"""
        dir_name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")

        if ok and dir_name:
            # Note: SD card operations might not support mkdir directly
            # This would depend on the sc64deployer tool capabilities
            QMessageBox.information(
                self, "Info",
                "Folder creation via mkdir may not be supported by sc64deployer.\n"
                "Please create folders through other means."
            )

    def _drag_enter_event(self, event):
        """Handle drag enter event for file drops"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event):
        """Handle file drop event for uploads"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                pc_path = url.toLocalFile()
                if os.path.isfile(pc_path):
                    self._upload_file_from_pc_path(pc_path)
            event.acceptProposedAction()

    def _execute_sd_operation(self, operation: str, args: List[str], success_message: str):
        """Execute an SD card operation in a background thread"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_changed.emit(f"Executing: {operation}...")

        self.worker_thread = QThread()
        self.worker = SDOperationWorker(self.exe_path, operation, args)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(lambda: self._on_operation_complete(success_message))
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

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

    def update_exe_path(self, new_exe_path: str):
        """Update the path to the sc64deployer executable"""
        self.exe_path = new_exe_path
