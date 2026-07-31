import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.widgets.main.containers import MTWidget

if t.TYPE_CHECKING:
    from src.config.manager import Config


class MTBaseSetting(MTWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Config,
        cfg_key: str,
        obj_name: str = '',
    ) -> None:
        super().__init__(parent, obj_name=obj_name)

        self._config = config
        self._cfg_key = cfg_key
