import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout

from .list import MTList
from .widget import MTWidget


class MTLabeledList(MTWidget): # remove this shit later
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent, obj_name=obj_name)

        self._build_ui(obj_name=obj_name)

    def _build_ui(
        self,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        self._main_layout = create_layout(LayoutType.VBOX, self)

        self.list_widget = MTList(self, obj_name=obj_name)
        self._main_layout.addWidget(self.list_widget)
        
        self._main_layout.addStretch()

    def set_items(self, items: t.Sequence[str], *, preferred: str | None = None) -> bool:
        target = preferred if preferred in items else items[0] if items else None
        if self._plain_values() == [str(item) for item in items]:
            self.list_widget.setCurrentValue(target)
            return False

        self.list_widget.clear()
        for name in items:
            self.list_widget.add_item(name, name)
        self.list_widget.setCurrentValue(target)
        return True

    def current_value(self) -> str | None:
        return self.list_widget.currentValue()

    def _plain_values(self) -> list[str]:
        return self.list_widget.plainValues()
