from PySide6.QtWidgets import QButtonGroup


class MTButtonGroup(QButtonGroup):
    def __init__(
        self,
        *,
        obj_name: str = '',
        exclusive: bool = True,
    ) -> None:
        super().__init__()
        self.setExclusive(exclusive)

        if obj_name:
            self.setObjectName(obj_name)
