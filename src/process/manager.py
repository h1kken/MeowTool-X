from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from utils.logger import logger

class ProcessManager(QObject):
    process_started = pyqtSignal(str)
    process_finished = pyqtSignal(str, int, QProcess.ExitStatus)
    process_output = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.processes: dict[str, QProcess] = {}

    def start_process(self, name: str, command: list[str]):
        if name in self.processes:
            logger.warning(f"Process {name} already running")
            return

        process = QProcess()
        process.setProgram(command[0])
        process.setArguments(command[1:])

        process.finished.connect(lambda code, status: self._on_finished(name, code, status))
        process.readyReadStandardOutput.connect(lambda: self._on_output(name))
        process.readyReadStandardError.connect(lambda: self._on_output(name, error=True))

        process.start()
        self.processes[name] = process
        self.process_started.emit(name)
        logger.debug(f"Successfully started process {name}")

    def _on_output(self, name: str, error: bool = False):
        process = self.processes.get(name)
        if not process:
            return
        data = process.readAllStandardError() if error else process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="ignore").strip()
        if text:
            self.process_output.emit(name, text)

    def _on_finished(self, name: str, code: int, status: QProcess.ExitStatus):
        self.processes.pop(name, None)
        self.process_finished.emit(name, code, status)
        logger.debug(f"Process {name} finished with code {code}")

    def terminate_process(self, name: str):
        process = self.processes.pop(name, None)
        if process:
            process.terminate()
            logger.debug(f"Successfully terminated process {name}")
            return True
        return False

    def terminate_all_processes(self):
        for name, process in list(self.processes.items()):
            process.terminate()
            logger.debug(f"Terminated process {name}")
        self.processes.clear()
