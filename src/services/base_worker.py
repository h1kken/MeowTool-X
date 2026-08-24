from PySide6.QtCore import QObject, Signal


class BaseWorker(QObject):
    progress = Signal(dict)
    finished = Signal(dict)

    def run(self) -> None:
        raise NotImplementedError
