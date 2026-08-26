from abc import abstractmethod

from PySide6.QtCore import QObject, Signal


class BaseWorker(QObject):
    runCreated = Signal(object)
    progress = Signal(dict)
    finished = Signal(dict)

    @abstractmethod
    def run(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def pause(self, paused: bool) -> None:
        ...
