from PySide6.QtWidgets import QButtonGroup

from src.utils.qt import build_object_name


class MTButtonGroup(QButtonGroup):
    def __init__(
        self,
        *,
        obj_name: tuple[str, ...] = (),
        exclusive: bool = True,
    ) -> None:
        super().__init__(exclusive=exclusive)
        self.setObjectName(build_object_name((*obj_name, 'ButtonGroup')))
