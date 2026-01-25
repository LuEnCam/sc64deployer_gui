# exec_runner.py

from PyQt6.QtCore import QObject, pyqtSignal, QThread
import subprocess, sys

class ExecWorker(QObject):
    output = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, exe_path, command, options=None):
        super().__init__()
        self.exe_path = exe_path
        self.command = command
        self.options = options or []
        self._process = None

    def set_properties(self, exe_path, command, options=None):
        self.exe_path = exe_path
        self.command = command
        self.options = options or []

    def run(self):
        try:
            cmd = []
            if sys.platform.startswith("linux"):
                cmd.append("pkexec")  # uses PolicyKit, shows a dialog

            cmd.extend([self.exe_path, self.command])
            cmd.extend(self.options)
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True
            )


            if self.command == "firmware" and "update" in self.options:
                try:
                    self._process.stdin.write("y\n")
                    self._process.stdin.flush()
                except Exception as e:
                    self.error.emit(f"Failed to send confirmation input: {e}")

            # Read stdout
            for line in self._process.stdout:
                self.output.emit(line)
            self._process.stdout.close()
            # Read stderr
            err = self._process.stderr.read()
            if err:
                self.error.emit(err)
            self._process.stderr.close()
            self._process.wait()
        except Exception as e:
            self.error.emit(str(e))
        self.finished.emit()

    def terminate(self):
        if self._process:
            self._process.terminate()
