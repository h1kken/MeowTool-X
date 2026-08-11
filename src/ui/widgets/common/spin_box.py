from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QDoubleSpinBox, QLineEdit, QSpinBox, QStyle, QStyleOptionSpinBox, QWidget

from src.utils.qt import build_object_name


def _text_render_width(widget: QWidget, values: tuple[str, ...]) -> int:
    metrics = widget.fontMetrics()
    widths = [metrics.horizontalAdvance(str(value)) for value in values if str(value)]
    return max(widths or [1])


def _line_edit_horizontal_margins(line_edit: QLineEdit) -> int:
    margins = line_edit.textMargins()
    return max(0, margins.left() + margins.right())


def _spin_box_text_safety_width(spin_box: QSpinBox | QDoubleSpinBox) -> int:
    metrics = spin_box.fontMetrics()
    return max(4, metrics.horizontalAdvance('0'))


def _spin_box_content_size_hint(spin_box: QSpinBox | QDoubleSpinBox, values: tuple[str, ...]) -> QSize:
    text_width = (
        _text_render_width(spin_box, values) +
        _line_edit_horizontal_margins(spin_box.lineEdit()) +
        _spin_box_text_safety_width(spin_box)
    )
    content_size = QSize(max(1, text_width), max(1, spin_box.fontMetrics().height()))

    option = QStyleOptionSpinBox()
    spin_box.initStyleOption(option)
    option.buttonSymbols = QSpinBox.ButtonSymbols.NoButtons
    option.frame = False

    return spin_box.style().sizeFromContents(
        QStyle.ContentsType.CT_SpinBox,
        option,
        content_size,
        spin_box,
    )


class MTSpinBox(QSpinBox):
    _OBJECT_NAME = 'SpinBox'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
    ) -> None:
        super().__init__(parent)
        self.setObjectName(build_object_name((*obj_name, MTSpinBox._OBJECT_NAME)))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

    def sizeHint(self) -> QSize:
        return _spin_box_content_size_hint(
            self,
            (
                self.textFromValue(self.minimum()),
                self.textFromValue(self.maximum()),
            ),
        )

    def minimumSizeHint(self) -> QSize:
        return _spin_box_content_size_hint(
            self,
            (
                self.textFromValue(self.minimum()),
                self.textFromValue(self.maximum()),
            ),
        )

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()
        self.clearFocus()
