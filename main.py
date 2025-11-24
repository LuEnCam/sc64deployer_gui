import sys
import shlex
from PyQt6.QtWidgets import ( 
    QApplication, QWidget, QGridLayout, QPushButton, QTextEdit, QLineEdit, QSpinBox,
    QHBoxLayout, QFileDialog, QLabel, QVBoxLayout, QMainWindow, 
    QGroupBox, QMenu, QWidgetAction
)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import QThread, QSettings, QSize
from exec_runner import ExecWorker

from sc64_lists_command_options import list_of_commands, list_of_options, list_of_parameters
from sc64_lists_command_options import Types

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
        self.run_command_button = QPushButton("Run Command")
        self.run_command_button.setEnabled(False)

        
        self.exe_label = QLabel("No .exe selected.")
        self.exe_version_label = QTextEdit("Version: N/A")
        self.notify = True

        self.options_of_command = [] # test
        self.parameters_of_options = [] # test

        self.button_group_commands = QGroupBox("Commands")
        self.group_options = QGroupBox("Options")
        self.group_parameters = QGroupBox("Parameters")
        self.button_layout = QGridLayout()
        self.options_layout = QGridLayout()
        self.parameter_layout = QGridLayout()
        self.button_group_commands.setLayout(self.button_layout)
        self.group_options.setLayout(self.options_layout)
        self.group_parameters.setLayout(self.parameter_layout)
        self.glayout.addWidget(self.button_group_commands, 0, 0, 1, 1)
        self.glayout.addWidget(self.group_options, 1, 0, 1, 1)
        self.glayout.addWidget(self.group_parameters, 2, 0, 1, 1)
        self.glayout.addWidget(self.run_command_button, 3, 0, 1, 1)
        self.buttons = []
        i = 0
        j = 0
        for cmd in list_of_commands:
            btn = QPushButton(cmd[0])
            btn.setToolTip(cmd[1])
            #btn.clicked.connect(self.run_command)
            btn.clicked.connect(lambda _, c=cmd[0], b=btn: 
                                (self.disable_run_button(),
                                 self.list_options(c), 
                                 self.update_button_color(b, self.buttons)))
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

    def update_button_color(self, btn: QPushButton, button_list):
        for b in button_list:
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
        self.clear_options_layout()
        self.clear_parameter_layout()
        options = [opt for opt in list_of_options if opt[0] == command and opt[1] != "---"]
        print(f"Size of options: {len(options)}")
        if options:
            if self.options_of_command:
                del self.options_of_command
            self.options_of_command = []
            i = 0
            j = 0
            for opt in options:
                str_of_opt_with_no_args = f"{opt[1]}"
                btn = QPushButton(str_of_opt_with_no_args)
                btn.setToolTip(opt[4])
                #btn.clicked.connect(self.run_command)
                btn.clicked.connect(lambda _, option=opt, b=btn:( self.list_parameters(command, option), self.update_button_color(b, self.options_of_command)))
                btn.setEnabled(True)
                self.options_layout.addWidget(btn, i, j)
                j += 1
                if j >= 4:
                    j = 0
                    i += 1
                self.options_of_command.append(btn)
        else: # If there are no options, run the command directly
            #self.run_command(command)
            self.enable_run_button(command)


    def list_parameters(self, command, option):
        self.disable_run_button()
        self.clear_parameter_layout()
        print(f"Size of params: {option[2]}")
        if option[2] > 0 or command == "upload" or command == "download" or command == "64dd":
            if self.parameters_of_options:
                del self.parameters_of_options
            self.parameters_of_options = []

            ## section for "upload" command (needs by default a path to ROM file)
            i = 0
            line_edit_of_rom = None
            if command == "upload" or command == "download" or command == "64dd":
                line_edit_of_rom = QLineEdit()
                line_edit_of_rom.setPlaceholderText("Path to ROM file")
                line_edit_of_rom.setDisabled(True)
                btn = QPushButton("Select ROM Path")
                params = [opt for opt in list_of_parameters if opt[0] == command and opt[1] == option[1]]
                if params or option[2] != 0:
                    btn.clicked.connect(lambda _: (
                        line_edit_of_rom.setText(QFileDialog.getOpenFileName(self, 'Select ROM File', '', 'ROM Files(*.z64 *.n64 *.v64 *.bin)')[0]),
                        self.disable_run_button()
                    ))
                else:
                    btn.clicked.connect(lambda _: (
                        line_edit_of_rom.setText(QFileDialog.getOpenFileName(self, 'Select ROM File', '', 'ROM Files(*.z64 *.n64 *.v64 *.bin)')[0]),
                        self.enable_run_button(command, f"{shlex.quote(line_edit_of_rom.text())}"))
                    )
                self.parameter_layout.addWidget(line_edit_of_rom, i, 0, 1, 3)
                self.parameter_layout.addWidget(btn, i, 3, 1, 1)
                i += 1
            j = 0
            if params: # Mostly for RADIO options
                for param in params[0][2]:
                    radio_btn = QPushButton(param)
                    #radio_btn.clicked.connect(lambda _, c=param: self.run_command(command, f"{option[1]} {c}"))
                    if line_edit_of_rom:
                        radio_btn.clicked.connect(lambda _, c=param: 
                                                  self.enable_run_button(command, f"{option[1]} {c} {shlex.quote(line_edit_of_rom.text())}"))
                    else:
                        radio_btn.clicked.connect(lambda _, c=param: 
                                                  self.enable_run_button(command, f"{option[1]} {c}"))
                    self.parameter_layout.addWidget(radio_btn, i, j)
                    j += 1
                    if j >= 4:
                        j = 0
                        i += 1
            else: # Mostly for non multiple choice options
                if option[2] > 0:
                    type_of_param: Types = option[3]
                    btn = None
                    if type_of_param == Types.TEXT:
                        btn = QLineEdit()
                        btn.setPlaceholderText(option[4])
                    elif type_of_param == Types.PATH_GET_LOCATION:
                        btn = QPushButton("Select File")
                        btn.setToolTip(option[4])
                        fdOptions = QFileDialog.Option.ShowDirsOnly
                        #btn.clicked.connect(lambda _,: self.run_command(command, f"{option[1]} {QFileDialog.getSaveFileName(self, "ROM selection", "All Files(*);;Text Files(*.txt)", options = fdOptions)[0]}") if command else "")                
                        if line_edit_of_rom:
                            btn.clicked.connect(lambda _,: self.enable_run_button(command, f"{option[1]} {shlex.quote(QFileDialog.getOpenFileName(self, "File selection", '')[0])} {shlex.quote(line_edit_of_rom.text())}") if command else "")   
                        else:
                            btn.clicked.connect(lambda _,: self.enable_run_button(command, f"{option[1]} {shlex.quote(QFileDialog.getOpenFileName(self, "File selection", '')[0])}") if command else "")                
                    elif type_of_param == Types.PATH_SET_LOCATION:
                        btn = QPushButton("Save File As...")
                        btn.setToolTip(option[4])
                        fdOptions = QFileDialog.Option.ShowDirsOnly
                        btn.clicked.connect(lambda _,: self.enable_run_button(command, f"{option[1]} {QFileDialog.getSaveFileName(self, "Location selection", "All Files(*)", options = fdOptions)[0]}") if command else "")                
                    elif type_of_param == Types.SPINNER:
                        btn = QSpinBox()
                        btn.setRange(0, 65535)
                    elif type_of_param == Types.ADDRESS:
                        btn = QLineEdit()
                        btn.setPlaceholderText("Enter address")
                    self.parameter_layout.addWidget(btn, i, j)
                    j += 1
                    if j >= 4:
                        j = 0
                        i += 1
                    self.parameters_of_options.append(btn)
        else: # If there are no parameters, run the command directly
            #self.run_command(command, option[1])
            self.enable_run_button(command, option[1])



    ### PROCESS PART ###

    def enable_run_button(self, command):
        self.run_command_button.setEnabled(True)
        self.run_command_button.setStyleSheet("background-color: lightgreen;")
        self.run_command_button.clicked.connect(lambda: self.run_command(command))

    def enable_run_button(self, command, options=""):
        self.run_command_button.setEnabled(True)
        self.run_command_button.setStyleSheet("background-color: lightgreen;")
        if self.run_command_button.receivers(self.run_command_button.clicked) > 0:
            self.run_command_button.clicked.disconnect()
        self.run_command_button.clicked.connect(lambda: self.run_command(command, options))

    def disable_run_button(self):
        self.run_command_button.setStyleSheet("")
        self.run_command_button.setEnabled(False)
        if self.run_command_button.receivers(self.run_command_button.clicked) > 0:
            self.run_command_button.clicked.disconnect()

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

    def run_command(self, command, options=""):
        if not self.exe_path:
            self.append_error("Please select sc64deployer.exe first.")
            return
        ## Special case for no command
        if command == '---' :
                command = list(options.split())[0]
                options = ""
                if len(list(options.split())) >= 2 and list(options.split())[1] is not None:
                    options = ' '.join(list(options.split())[1:])
        self.text_output.append(f"\n[CMD] {command} {options}")
        self.text_output.moveCursor(QTextCursor.MoveOperation.End)
        for btn in self.buttons:
            btn.setEnabled(False)

        self.start_worker(command, options=options)

    def start_worker(self, command, options = "", notify=True):
        self.notify = notify
        # Clean up previous thread if any
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        # Set up new worker and thread
        args = shlex.split(options) if options else []
        self.worker = ExecWorker(self.exe_path, command, args)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.output.connect(self.append_output)
        self.worker.error.connect(self.append_error)
        self.worker.finished.connect(self.process_finished)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()


    ### END PROCESS PART ###





    ### CONSOLE OUTPUT PART ###

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

    ### END CONSOLE OUTPUT PART ###




    def process_finished(self):
        for btn in self.buttons:
            btn.setEnabled(True)
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None

    def clear_options_layout(self):
        for i in reversed(range(self.options_layout.count())): 
            self.options_layout.itemAt(i).widget().setParent(None)
    
    def clear_parameter_layout(self):
        for i in reversed(range(self.parameter_layout.count())): 
            self.parameter_layout.itemAt(i).widget().setParent(None)


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


    ### SETTINGS PART ###


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
    
    
    ### END SETTINGS PART ###
        
    def run(self):
        self.window.show()
        self.app.exec()
        self.write_settings()



app = SC64MainWindow()
app.run()
