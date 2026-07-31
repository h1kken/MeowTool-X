import typing as t

from PySide6.QtWidgets import QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTList, MTWidget


_GROUP_ITEM_INDENT = '   '


class MTLabeledList(MTWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: str = '',
    ) -> None:
        super().__init__(parent, obj_name=obj_name)

        layout = create_layout(LayoutType.VBOX, self)

        self.list_widget = MTList(self, obj_name=obj_name)
        layout.addWidget(self.list_widget)

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

    def set_grouped_items(self, groups: t.Sequence[tuple[str, t.Sequence[tuple[str, str]]]], *, preferred: str | None = None) -> None:
        available_values = [
            value
            for _, items in groups
            for _, value in items
        ]
        target = preferred if preferred in available_values else (available_values[0] if available_values else None)

        self.list_widget.clear()
        is_first_group = True
        for group_label, group_items in groups:
            if group_label.strip():
                if not is_first_group and self.list_widget.count() > 0:
                    self.list_widget.add_spacer()
                self.list_widget.add_header(group_label)

            for display_text, value in group_items:
                self.list_widget.add_item(f'{_GROUP_ITEM_INDENT}{display_text}', value)

            is_first_group = False

        self.list_widget.setCurrentValue(target)

    def current_value(self) -> str | None:
        return self.list_widget.currentValue()

    def _plain_values(self) -> list[str]:
        return self.list_widget.plainValues()
