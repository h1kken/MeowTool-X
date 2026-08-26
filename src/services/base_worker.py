from PySide6.QtCore import QObject, Signal


class BaseWorker(QObject):
    run_created = Signal(object)
    progress = Signal(dict)
    finished = Signal(dict)

    def run(self) -> None:
        raise NotImplementedError
