import pathlib
import sys
import shlex
import time
from PyQt6.QtWidgets import ( 
    QApplication, QWidget, QGridLayout, QPushButton, QTextEdit, QLineEdit, QSpinBox,
    QHBoxLayout, QFileDialog, QLabel, QVBoxLayout, QMainWindow, 
    QGroupBox, QMenu, QWidgetAction, QMessageBox
)
from PyQt6.QtGui import QTextCursor, QIcon
from PyQt6.QtCore import QThread, QSettings, QSize
from exec_runner import ExecWorker

from sc64_lists_command_options import list_of_commands, list_of_options, list_of_parameters
from sc64_lists_command_options import Types
import os
import tempfile
import zipfile, tarfile
import requests
from packaging import version  # pip install packaging
from pathlib import Path

SC64_GITHUB_API_LATEST = "https://api.github.com/repos/Polprzewodnikowy/SummerCart64/releases/latest"
SC64MENU_GITHUB_API_LATEST = "https://api.github.com/repos/Polprzewodnikowy/N64FlashcartMenu/releases/latest"

class SC64MainWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self) # call the superclass constructor

        self.SYSTEM_NAME = sys.platform
        if self.SYSTEM_NAME.startswith("win"):
            self.SYSTEM_NAME = "windows"
        elif self.SYSTEM_NAME.startswith("linux"):
            self.SYSTEM_NAME = "linux"
        elif self.SYSTEM_NAME.startswith("darwin"):
            self.SYSTEM_NAME = "macos"

        self.current_path = os.getcwd()

        print(f"Current path: {self.current_path}")

        self.latest_version = None

        self.glayout = QGridLayout()

        self.group_output = QGroupBox("Sc64deployer Output")
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
        self.filename_savepath = None

        
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
        
        if btn:
            btn.setStyleSheet("background-color: green;")

    def disable_buttons(self):
        for btn in self.buttons:
            btn.setEnabled(False)

    def enable_buttons(self):
        for btn in self.buttons:
            btn.setEnabled(True)

    def select_exe(self):
        if self.SYSTEM_NAME == "windows":
            exe_path, _ = QFileDialog.getOpenFileName(self, "Select sc64deployer.exe", "", "Executables (*.exe)")
        elif self.SYSTEM_NAME == "linux" or self.SYSTEM_NAME == "macos":
            exe_path, _ = QFileDialog.getOpenFileName(self, "Select sc64deployer executable", "", "All Files(*)")
        if exe_path:
            self.exe_path = exe_path
            self.check_set_exe()

    def check_set_exe(self):
        if self.exe_path:
            if self.exe_path and (not "sc64deployer" in os.path.basename(self.exe_path) or "sc64deployer_gui" in os.path.basename(self.exe_path)):
                self.exe_version_label.setText("Version: N/A")
                self.exe_path = None
                self.clear_parameter_layout()
                self.clear_options_layout()
                self.text_output.clear()
                self.update_button_color(None, self.buttons)
                self.disable_buttons()
                self.disable_run_button()
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("Invalid deployer")
                msg.setText("The selected deployer is not the sc64deployer")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()
                return
            self.exe_label.setText(f"Path of deployer: {self.exe_path}")
            self.start_worker("--version", notify=False)
            self.enable_buttons()


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
            params = None
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
                    btn2 = None
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
                        btn.clicked.connect(lambda _,: self.enable_run_button(command, f"{option[1]} {shlex.quote(self.set_save_file_path())}") if command else "")                
                    elif type_of_param == Types.PATH_SD:
                        btn = QLineEdit()
                        btn.setPlaceholderText("Path on SD Card (\"/\" for root)")
                        btn.textChanged.connect(lambda _: self.enable_run_button(command, f"{option[1]} {shlex.quote(btn.text())}"))
                    elif type_of_param == Types.PATH_SD_DUO:
                        btn = QLineEdit()
                        btn.setPlaceholderText("Path SOURCE on SD Card (\"/\" for root)")
                        btn.textChanged.connect(lambda _: self.enable_run_button(command, f"{option[1]} {shlex.quote(btn.text())} {shlex.quote(btn2.text())}"))
                        btn2 = QLineEdit()
                        btn2.setPlaceholderText("Path DESTINATION on SD Card (\"/\" for root)")
                        btn2.textChanged.connect(lambda _: self.enable_run_button(command, f"{option[1]} {shlex.quote(btn.text())} {shlex.quote(btn2.text())}"))
                    elif type_of_param == Types.PATH_SD_PC:
                        btn = QLineEdit()
                        btn.setPlaceholderText("Path SOURCE on SD Card (\"/\" for root)")
                        btn.textChanged.connect(lambda _: self.enable_run_button(command, f"{option[1]} {shlex.quote(btn.text())} {shlex.quote(self.filename_savepath)}") if command else "")
                        btn2 = QPushButton("Save File As...")
                        btn2.setToolTip(option[4])
                        btn2.clicked.connect(lambda _,: self.enable_run_button(command, f"{option[1]} {shlex.quote(btn.text())} {shlex.quote(self.set_save_file_path())}") if command else "")
                    elif type_of_param == Types.PATH_PC_SD:
                        line_edit_of_rom = QLineEdit()
                        line_edit_of_rom.setPlaceholderText("Path to ROM file")
                        line_edit_of_rom.setDisabled(True)
                        btn = QPushButton("Select File")
                        btn.setToolTip(option[4])
                        if line_edit_of_rom:
                            btn.clicked.connect(lambda _,: (
                                line_edit_of_rom.setText(QFileDialog.getOpenFileName(self, 'Select File', '', '')[0]),
                                self.enable_run_button(command, f"{option[1]} {shlex.quote(line_edit_of_rom.text())} {shlex.quote(btn2.text())}") if command else ""
                                ))                                                                                          
                        btn2 = QLineEdit()
                        btn2.setPlaceholderText("Path DESTINATION on SD Card (\"/\" for root)")
                        btn2.textChanged.connect(lambda _: self.enable_run_button(command, f"{option[1]} {shlex.quote(line_edit_of_rom.text())} {shlex.quote(btn2.text())}"))
                    elif type_of_param == Types.SPINNER:
                        btn = QSpinBox()
                        btn.setRange(0, 65535)
                    elif type_of_param == Types.ADDRESS:
                        btn = QLineEdit()
                        btn.setPlaceholderText("Enter address")
                    
                    if line_edit_of_rom:
                        self.parameter_layout.addWidget(line_edit_of_rom, i, 0, 1, 3)
                        self.parameter_layout.addWidget(btn, i, 3, 1, 1)
                    else:
                        self.parameter_layout.addWidget(btn, i, j, 1, 3)
                    if btn2:
                        i += 1
                        j = 0
                        self.parameter_layout.addWidget(btn2, i, j, 1, 3)
                    j += 1
                    if j >= 4:
                        j = 0
                        i += 1
                    self.parameters_of_options.append(btn)
        else: # If there are no parameters, run the command directly
            #self.run_command(command, option[1])
            self.enable_run_button(command, option[1])


    ### Utilites PART ###
    def set_save_file_path(self) -> str:
        fdOptions = QFileDialog.Option.ShowDirsOnly
        self.filename_savepath = QFileDialog.getSaveFileName(self, "Location selection", "", "All Files(*)", options = fdOptions)[0]
        return self.filename_savepath

    ### END UTILITIES PART ###

    ### PROCESS PART ###

    def enable_run_button(self, command):
        self.run_command_button.setEnabled(True)
        self.run_command_button.setStyleSheet("background-color: green;")
        self.run_command_button.clicked.connect(lambda: self.run_command(command))

    def enable_run_button(self, command, options=""):
        self.run_command_button.setEnabled(True)
        self.run_command_button.setStyleSheet("background-color: green;")
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
        self.disable_buttons()
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
        self.disable_buttons()

        self.start_worker(command, options=options)

    def start_worker(self, command, options="", notify=True, on_done=None):
        self.notify = notify

        # Optional: prevent overlapping runs
        if self.worker_thread and self.worker_thread.isRunning():
            self.append_error("A command is already running.")
            return

        args = shlex.split(options) if options else []

        # Create NEW instances each time (avoid moveToThread issues)
        self.worker_thread = QThread(self)
        self.worker = ExecWorker(self.exe_path, command, args)  # NEW worker
        self.worker.moveToThread(self.worker_thread)

        self.worker.output.connect(self.append_output)
        self.worker.error.connect(self.append_error)

        # When worker finishes, stop thread + cleanup
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        # Your "next step"
        if on_done:
            self.worker.finished.connect(on_done)

        # Final UI cleanup when thread is fully done
        self.worker_thread.finished.connect(self.process_finished)

        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

        self.reset_self_vars()


    def reset_self_vars(self):
        self.filename_savepath = None

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
        self.enable_buttons()
        self.worker_thread = None
        self.worker = None

    def clear_options_layout(self):
        for i in reversed(range(self.options_layout.count())): 
            self.options_layout.itemAt(i).widget().setParent(None)
    
    def clear_parameter_layout(self):
        for i in reversed(range(self.parameter_layout.count())): 
            self.parameter_layout.itemAt(i).widget().setParent(None)


    def check_firmware_update(self):
        print(f"Checking for firmware updates on system: {self.SYSTEM_NAME}")
        self.text_output.clear()
        try:
            # extracting version from firmware on sc64 cart:
            self.start_worker(
                "info",
                "",
                notify=True,
                on_done=self.do_next_thing_firmware
            )

        except:
            return None



    def do_next_thing_firmware(self):
        # extract firmware version from text output
        local_firmware_version = "N/A"
        is_powered_on = False
        for line in self.text_output.toPlainText().splitlines():
            if "Current CIC step:" in line:
                value = line.split("Current CIC step:")[-1].strip()
                is_powered_on = value != "Power off"
            if "Firmware version:" in line:
                local_firmware_version = line.split("Firmware version:")[-1].strip()
        print(f"sc64 firmware version on console: {local_firmware_version}")

        if local_firmware_version == "N/A" or is_powered_on:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Update check")
            msg.setText("Could not retrieve sc64 firmware version from your cartridge.")
            msg.setInformativeText("Please make sure:\n" \
            "- You have correctly set a sc64deployer to be used with the GUI\n" \
            "- The SC64 device is connected to your device through USB.\n" \
            "- If the SC64 is connected to a N64 that the console is powered OFF.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            return

        local_firmware_version = local_firmware_version.lstrip("v")

        # compare versions
        try: 
            resp = requests.get(SC64_GITHUB_API_LATEST, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            latest_tag = data["tag_name"]          # e.g. "v1.2.3"
            latest_version = latest_tag.lstrip("v")  # -> "1.2.3"

            if version.parse(latest_version) > version.parse(local_firmware_version):
                print(f"New firmware version available: {latest_version}")
                download_url = None
                for asset in data.get("assets", []):
                    if "sc64-firmware" in asset["name"]:
                        download_url = asset["browser_download_url"]
                        break
                text = (
                    f"A new version of the sc64 firmware is available.\n\n"
                    f"Version on your sc64:     {local_firmware_version}\n"
                    f"Latest version:           {latest_version}\n\n"
                    f"Download URL:\n{download_url}"
                )
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("sc64 firmware Update available")
                msg.setText(text)
                msg.setInformativeText("Click OK to download and update the sc64 firmware on your summercart64.")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok |
                                    QMessageBox.StandardButton.Cancel)
                ret = msg.exec()

                if ret == QMessageBox.StandardButton.Ok:
                    fd, temp_path = tempfile.mkstemp(suffix=".bin")
                    os.close(fd)  # we will reopen it normally

                    resp = requests.get(download_url, stream=True)
                    resp.raise_for_status()

                    with open(temp_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    self.latest_version = latest_version

                    # running the firmware update command
                    self.start_worker("firmware", f"update {shlex.quote(temp_path)}", notify=True, on_done=self.confirm_update_message)

            else:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Update check")
                msg.setText("Your sc64 firmware is already up to date (version " + local_firmware_version + ").")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()

        except:
            # inform failed to get update
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Update check")
            msg.setText("Could not check for firmware updates.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            return 


    def confirm_update_message(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Update check")
        msg.setText("sc64 firmware has been updated to version " + self.latest_version + ".")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

        self.latest_version = None

    def check_deployer_update(self):
        print(f"Checking for updates on system: {self.SYSTEM_NAME}")
        try:
            resp = requests.get(SC64_GITHUB_API_LATEST, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            latest_tag = data["tag_name"]          # e.g. "v1.2.3"
            latest_version = latest_tag.lstrip("v")  # -> "1.2.3"

            local_version = self.exe_version_label.toPlainText().replace("Version: sc64deployer ", "").strip()
            print(f"Local version: {local_version}")
            LOCAL_VERSION = local_version if local_version != "Version: N/A" else "0.0"

            # Find the .exe asset download URL
            exe_asset = None
            for asset in data.get("assets", []):
                if self.SYSTEM_NAME in asset["name"]:
                    exe_asset = asset
                    break

            if not exe_asset:
                print("No .exe asset found in latest release.")
                return None, None, None

            download_url = exe_asset["browser_download_url"]

            if version.parse(latest_version) > version.parse(LOCAL_VERSION):
                print(f"New version available: {latest_version}")
                print(f"Download URL: {download_url}")
                return latest_version, download_url, data
            else:
                print("Already up to date.")
                return None, None, data

        except Exception as e:
            print(f"Could not check for updates: {e}")
            return None, None, None
        

    def find_bytes_offset(self, file_path: str, hex_string: str):
        # Convert hex string → bytes
        pattern = bytes.fromhex(hex_string)

        with open(file_path, "rb") as f:
            data = f.read()  # read entire file into memory

        # Find offset
        offset = data.find(pattern)
        return offset  # -1 if not found
    

    def on_check_update_sc64menu_clicked(self):
        path = ''
        if self.SYSTEM_NAME == "windows":
            path = "temp.n64"
        else:
            path = pathlib.Path.home() / "temp.n64"
        #self.start_worker("sd", f"download /sc64menu.n64 {path}", notify=True)
        self.start_worker(
            "sd",
            f"download /sc64menu.n64 {path}",
            notify=True,
            on_done=self.do_next_thing
        )
        
    def do_next_thing(self):
        path = ''
        if self.SYSTEM_NAME == "windows":
            path = "temp.n64"
        else:
            path = pathlib.Path.home() / "temp.n64"
        if not os.path.exists(path):
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Update check")
            msg.setText("Could not find sc64menu.n64 on the SD card.")
            msg.setInformativeText("Please make sure:\n" \
            "- You're using the sc64deployer version v2.20.0 or newer.\n" \
            "- sc64menu.n64 is present on the SD card.\n" \
            "- The SD card is properly inserted into the SC64 device.\n" \
            "- The SC64 device is connected to your device through USB.\n" \
            "- If the SC64 is connected to a N64 that the console is powered OFF.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            return
                        
        hex_pattern = "4D49543200F30C0000"  # same as your sequence, no spaces
        offset = self.find_bytes_offset(path, hex_pattern)
        second_offset = 0

        if offset != -1:
            print(f"Found at offset: 0x{offset:08X} ({offset} decimal)")
            second_offset = 9
        else:
            print("Pattern not found... retrying...")
            hex_pattern = "4D49543200F30B00"
            offset = self.find_bytes_offset(path, hex_pattern)
            if offset != -1:
                print(f"Found at offset: 0x{offset:08X} ({offset} decimal)")
                second_offset = 8
            else:
                print("Pattern not found... retrying...")
                hex_pattern = "4D4954320004E910F30A"
                offset = self.find_bytes_offset(path, hex_pattern)
                if offset != -1:
                    print(f"Found at offset: 0x{offset:08X} ({offset} decimal)")
                    second_offset = 10
                else:
                    print("Pattern not found... retrying...")
                    hex_pattern = "4D49543200F0080000"
                    offset = self.find_bytes_offset(path, hex_pattern)
                    if offset != -1:
                        print(f"Found at offset: 0x{offset:08X} ({offset} decimal)")
                        second_offset = 9
                    else:
                        print("Pattern not found... sorry...")
                        msg = QMessageBox(self)
                        msg.setIcon(QMessageBox.Icon.Critical)
                        msg.setWindowTitle("Update check")
                        msg.setText("Could not verify a new version of sc64menu.n64...")
                        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                        msg.exec()
                        return
        
        address = offset + second_offset # offset to version string
        print(f"Version string address: 0x{address:08X}")

        with open(path, "rb") as f:
            f.seek(address)          # jump to offset
            data = f.read(10)         # read 10 bytes
        date_on_current_version = data.decode("ascii", errors="replace")
        print(date_on_current_version)

        try:
            resp = requests.get(SC64MENU_GITHUB_API_LATEST, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            body_value = data.get("published_at")

            latest_version = body_value[:10] # e.g. "2024-06-15"

            # Extract version from body text (on line built from latest commit on main branch as of xxx-yy-zz)
            # latest_version = None
            # for line in body_value.splitlines():
            #     if line.startswith("built from latest commit on main branch as of"):
            #         latest_version = line.replace("built from latest commit on main branch as of", "").strip()
            #         latest_version = latest_version.replace(".", "").strip()
            #         break
            # if not latest_version:
            #     print("Could not find version in release notes.")
            #     return
            
            print(f"Latest sc64menu version found online: {latest_version}")

            if int(latest_version.replace("-","")) > int(date_on_current_version.replace("-","")):
                download_url = None
                for asset in data.get("assets", []):
                    if "sc64menu.n64" in asset["name"]:
                        download_url = asset["browser_download_url"]
                        break
                text = (
                    f"A new version of sc64menu.n64 is available.\n\n"
                    f"Current version date: {date_on_current_version}\n"
                    f"Latest version date: {latest_version}\n\n"
                    f"Download URL:\n{download_url}"
                )
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("sc64menu Update available")
                msg.setText(text)
                msg.setInformativeText("Click OK to download and update the sc64menu.n64 on your summercart64 SD card.")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok |
                                    QMessageBox.StandardButton.Cancel)
                ret = msg.exec()

                if ret == QMessageBox.StandardButton.Ok:
                    fd, temp_path = tempfile.mkstemp(suffix=".n64")
                    os.close(fd)  # we will reopen it normally

                    resp = requests.get(download_url, stream=True)
                    resp.raise_for_status()

                    with open(temp_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    # save file (not asking for location, just overwrite)
                    self.start_worker("sd", f"upload {shlex.quote(temp_path)} /sc64menu.n64", notify=True)

                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.setWindowTitle("Update check")
                    msg.setText("sc64menu.n64 has been updated on the SD card.")
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.exec()

            else:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Update check")
                msg.setText(f"You already have the latest version of sc64menu.n64.")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()

            os.remove(path)
                    

        except Exception as e:
            print(f"Could not check for updates: {e}")
            return None, None, None
        


    def on_check_updates_clicked(self):
        latest, url, _ = self.check_deployer_update()

        can_download = False
        if latest:
            text = (
                f"A new version {latest} is available.\n\n"
                f"Download URL:\n{url}"
            )
            can_download = True
        else:
            text = f"You already have the latest version of the sc64deployer."

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Update check")
        msg.setText(text)

        if can_download:
            msg.setInformativeText("Click OK to download and unpack the new version.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok |
                                QMessageBox.StandardButton.Cancel)
            ret = msg.exec()

            if ret == QMessageBox.StandardButton.Ok:
                # 1) Ask user where to extract
                target_dir = QFileDialog.getExistingDirectory(
                    self,
                    "Choose folder to unpack the new version"
                )
                if not target_dir:
                    return  # user cancelled

                try:
                    # 2) Download zip
                    zip_path = self.download_zip(url)

                    # 3) Extract
                    self.extract_zip(zip_path, target_dir)

                    if self.SYSTEM_NAME == "windows":
                        self.exe_path = os.path.join(target_dir, "sc64deployer.exe")
                        
                    elif self.SYSTEM_NAME == "linux" or self.SYSTEM_NAME == "macos":
                        self.exe_path = os.path.join(target_dir, "sc64deployer")

                    self.check_set_exe()

                    # 4) Tell user
                    done = QMessageBox(self)
                    done.setIcon(QMessageBox.Icon.Information)
                    done.setWindowTitle("Update completed")
                    done.setText(f"New version {latest} has been unpacked to:\n{target_dir}")
                    done.setStandardButtons(QMessageBox.StandardButton.Ok)
                    done.exec()

                except Exception as e:
                    err = QMessageBox(self)
                    err.setIcon(QMessageBox.Icon.Critical)
                    err.setWindowTitle("Update failed")
                    err.setText("An error occurred while downloading or unpacking the update.")
                    err.setInformativeText(str(e))
                    err.setStandardButtons(QMessageBox.StandardButton.Ok)
                    err.exec()

            return

        else:
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

    def download_zip(self, url: str) -> str:
        """
        Download an archive (zip or tar.gz) from `url` to a temp file.
        Returns the path to the temp file.
        """
        # Use a neutral suffix; extension doesn't matter to Python
        fd, temp_path = tempfile.mkstemp()
        os.close(fd)

        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()

        with open(temp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return temp_path


    def extract_zip(self, archive_path: str, target_dir: str) -> None:
        """
        Extract either a .zip or .tar.gz (or .tar) into target_dir.
        """
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(target_dir)
        elif tarfile.is_tarfile(archive_path):
            # tarfile auto-detects gzip, bzip2, etc.
            with tarfile.open(archive_path, "r:*") as tf:
                tf.extractall(target_dir)
        else:
            raise ValueError(f"File '{archive_path}' is not a valid zip or tar archive")

class SC64MainWindow():
    def __init__(self):
        self.app = QApplication([])
        self.window = QMainWindow()
        self.window.setWindowTitle("sc64deployer GUI")
        self.window.resize(700, 500)
        #icon_path = os.path.join(sys._MEIPASS, 'sc64.ico')
        #self.window.setWindowIcon(QIcon(icon_path))

        self.main_widget = SC64MainWidget()
        self.window.setCentralWidget(self.main_widget)

        self.select_exe_action = QWidgetAction(self.window)
        self.select_exe_action.setText("Select sc64deployer")
        self.select_exe_action.triggered.connect(self.main_widget.select_exe)

        self.check_deployer_update = QWidgetAction(self.window)
        self.check_deployer_update.setText("Verify update for sc64deployer")
        self.check_deployer_update.triggered.connect(self.main_widget.on_check_updates_clicked)

        self.check_sc64menu_update = QWidgetAction(self.window)
        self.check_sc64menu_update.setText("Verify update for sc64menu.n64")
        self.check_sc64menu_update.triggered.connect(self.main_widget.on_check_update_sc64menu_clicked)

        self.check_sc64menu_firmware = QWidgetAction(self.window)
        self.check_sc64menu_firmware.setText("Verify update for sc64 firmware")
        self.check_sc64menu_firmware.triggered.connect(self.main_widget.check_firmware_update)


        self.exe_version = QMenu(self.main_widget.exe_version_label.toPlainText())
        self.exe_version.setDisabled(True)

        self.main_widget.exe_version_label.textChanged.connect(
            lambda: self.exe_version.setTitle(self.main_widget.exe_version_label.toPlainText())
        )
        
        self.file_menu = QMenu("File")
        self.file_menu.addAction(self.select_exe_action)
        self.help_menu = QMenu("Help")
        self.help_menu.addAction(self.check_deployer_update)
        self.help_menu.addAction(self.check_sc64menu_update)
        self.help_menu.addAction(self.check_sc64menu_firmware)

        self.window.menuBar().setNativeMenuBar(True)
        self.window.menuBar().addMenu(self.file_menu)
        self.window.menuBar().addMenu(self.help_menu)
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
        print(f"settings: {settings.fileName()}")
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
