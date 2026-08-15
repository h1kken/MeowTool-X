from PySide6.QtCore import QObject, Signal


class BaseWorker(QObject):
    finished = Signal()

    def run(self) -> None:
        raise NotImplementedError
