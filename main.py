import sys
from PyQt6.QtWidgets import ( 
    QApplication, QWidget, QGridLayout, QPushButton, QTextEdit, 
    QHBoxLayout, QFileDialog, QLabel, QVBoxLayout, QMainWindow, 
    QGroupBox, QMenu, QWidgetAction
)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import QThread, QSettings, QSize
from exec_runner import ExecWorker

from sc64_lists_command_options import list_of_commands, list_of_options

class SC64MainWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self) # call the superclass constructor

        self.glayout = QGridLayout()

        self.group_output = QGroupBox("Console Output")
        self.group_output_layout = QGridLayout()
        self.group_output.setLayout(self.group_output_layout)
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        self.group_output_layout.addWidget(self.text_output, 1, 0, 1, 2)
        self.glayout.addWidget(self.group_output, 0, 1, 5, 2)
        self.clear_output_button = QPushButton("Clear Output")
        self.clear_output_button.clicked.connect(self.text_output.clear)
        self.group_output_layout.addWidget(self.clear_output_button, 0, 1, 1, 1)

        
        self.exe_label = QLabel("No .exe selected.")
        self.exe_version_label = QTextEdit("Version: N/A")
        self.notify = True

        self.options_of_command = [] # test

        self.button_group_commands = QGroupBox("Commands")
        self.group_options = QGroupBox("Options")
        self.button_layout = QGridLayout()
        self.options_layout = QGridLayout()
        self.button_group_commands.setLayout(self.button_layout)
        self.group_options.setLayout(self.options_layout)
        self.glayout.addWidget(self.button_group_commands, 0, 0, 1, 1)
        self.glayout.addWidget(self.group_options, 1, 0, 1, 1)
        self.buttons = []
        i = 0
        j = 0
        for cmd in list_of_commands:
            btn = QPushButton(cmd[0])
            btn.setToolTip(cmd[1])
            #btn.clicked.connect(self.run_command)
            btn.clicked.connect(lambda _, c=cmd[0], b=btn: 
                                (self.list_options(c), 
                                 self.update_button_color(b)))
            btn.setEnabled(False)
            self.button_layout.addWidget(btn, i, j)
            j += 1
            if j >= 4:
                j = 0
                i += 1
            self.buttons.append(btn)

        # For managing worker thread
        self.worker_thread = None
        self.worker = None

        self.setLayout(self.glayout)

    def update_button_color(self, btn: QPushButton):
        for b in self.buttons:
            b.setStyleSheet("")
        
        btn.setStyleSheet("background-color: green;")

    def select_exe(self):
        exe_path, _ = QFileDialog.getOpenFileName(self, "Select sc64deployer.exe", "", "Executables (*.exe)")
        if exe_path:
            self.exe_path = exe_path
            self.check_set_exe()

    def check_set_exe(self):
        if self.exe_path:
            self.exe_label.setText(f"Path of exe: {self.exe_path}")
            self.start_worker("--version", notify=False)
            for btn in self.buttons:
                btn.setEnabled(True)


    def list_options(self, command):
        for i in reversed(range(self.options_layout.count())): 
            self.options_layout.itemAt(i).widget().setParent(None)
        options = [opt for opt in list_of_options if opt[0] == command and opt[1] != "---"]
        if options:
            if self.options_of_command:
                del self.options_of_command
            self.options_of_command = []
            i = 0
            j = 0
            for opt in options:
                str_of_opt_with_no_args = f"{opt[1]} {opt[2]}"
                btn = QPushButton(str_of_opt_with_no_args)
                btn.setToolTip(opt[3])
                #btn.clicked.connect(self.run_command)
                btn.clicked.connect(lambda _, c=str_of_opt_with_no_args: print(f"Option '{c}' selected for command '{command}'"))
                btn.setEnabled(True)
                self.options_layout.addWidget(btn, i, j)
                j += 1
                if j >= 4:
                    j = 0
                    i += 1
                self.options_of_command.append(btn)


    def run_command(self):
        if not self.exe_path:
            self.append_error("Please select sc64deployer.exe first.")
            return
        sender = self.sender()
        cmd = sender.text()
        self.text_output.append(f"\n[CMD] {cmd}")
        self.text_output.moveCursor(QTextCursor.MoveOperation.End)
        for btn in self.buttons:
            btn.setEnabled(False)
        self.start_worker(cmd)

    def start_worker(self, command, notify=True):
        self.notify = notify
        # Clean up previous thread if any
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        # Set up new worker and thread
        self.worker = ExecWorker(self.exe_path, command)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.output.connect(self.append_output)
        self.worker.error.connect(self.append_error)
        self.worker.finished.connect(self.process_finished)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    def append_output(self, text):
        if self.notify:
            self.text_output.append(f"{text.strip()}")
            self.text_output.moveCursor(QTextCursor.MoveOperation.End)
        else:
            self.exe_version_label.setText(f"Version: {text.strip()}")

        self.notify = True
        

    def append_error(self, text):
        self.text_output.append(f"{text.strip()}")
        self.text_output.moveCursor(QTextCursor.MoveOperation.End)

    def process_finished(self):
        for btn in self.buttons:
            btn.setEnabled(True)
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None


class SC64MainWindow():
    def __init__(self):
        self.app = QApplication([])
        self.window = QMainWindow()
        self.window.setWindowTitle("sc64deployer GUI")
        self.window.resize(700, 500)

        self.main_widget = SC64MainWidget()
        self.window.setCentralWidget(self.main_widget)

        self.select_exe_action = QWidgetAction(self.window)
        self.select_exe_action.setText("Select sc64deployer.exe")
        self.select_exe_action.triggered.connect(self.main_widget.select_exe)

        self.exe_version = QMenu(self.main_widget.exe_version_label.toPlainText())
        self.exe_version.setDisabled(True)

        self.main_widget.exe_version_label.textChanged.connect(
            lambda: self.exe_version.setTitle(self.main_widget.exe_version_label.toPlainText())
        )
        
        self.file_menu = QMenu("File")
        self.file_menu.addAction(self.select_exe_action)

        self.window.menuBar().setNativeMenuBar(True)
        self.window.menuBar().addMenu(self.file_menu)
        self.window.menuBar().addMenu(self.exe_version)

        self.window.statusBar().addPermanentWidget(self.main_widget.exe_label, 1)

        self.read_settings()    # read the settings

        self.main_widget.check_set_exe()  # Check if exe is set


    ### Settings management
    def write_settings(self):
        settings = QSettings("SC64 deployer Gui", "Settings")
        settings.beginGroup("MainWindow")
        settings.setValue("exe_path", self.main_widget.exe_path)
        settings.setValue("size", self.window.size())
        settings.endGroup()

        #settings.clear()  # Clear settings to avoid memory leaks


    def read_settings(self):
        settings = QSettings("SC64 deployer Gui", "Settings")
        settings.beginGroup("MainWindow")
        self.main_widget.exe_path = settings.value("exe_path", None)
        self.window.resize(settings.value("size", QSize(800, 600)))
    ###########
        

    def run(self):
        self.window.show()
        self.app.exec()
        self.write_settings()



app = SC64MainWindow()
app.run()
