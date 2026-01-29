from typing import Optional
from PySide6.QtCore import Qt, QRect, QPointF
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton,
    QCheckBox, QSlider, QLineEdit,
    QSpinBox, QDoubleSpinBox, QStyle,
    QStyleOptionSlider,
)
from src.translation import TranslatableMixin


class MTLabel(TranslatableMixin, QLabel):
    def __init__(self, tr_key: str, *args, obj_name: Optional[str] = None, **kwargs) -> None:
        super().__init__(tr_key, *args, **kwargs)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name is not None:
            self.setObjectName(obj_name)
        
        
class MTButton(TranslatableMixin, QPushButton):
    def __init__(self, tr_key: str, *args, checkable: bool = False, checked: bool = False, obj_name: Optional[str] = None, **kwargs) -> None:
        super().__init__(tr_key, *args, **kwargs)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if checkable:
            self.setCheckable(True)
            self.setChecked(checked)

        if obj_name is not None:
            self.setObjectName(obj_name)
        
        
class MTCheckBox(QCheckBox):
    def __init__(self, *args, obj_name: Optional[str] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name is not None:
            self.setObjectName(obj_name)


class MTSlider(QSlider):
    def __init__(self, *args, obj_name: Optional[str] = None, **kwargs) -> None:
        super().__init__(Qt.Orientation.Horizontal, *args, **kwargs)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name is not None:
            self.setObjectName(obj_name)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._jump_to_cursor(event.position())
            event.accept()
        super().mousePressEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()
    
    def _jump_to_cursor(self, pos: QPointF):
        handle = self._handle_rect()
        
        if self.orientation() == Qt.Orientation.Horizontal:
            slider_len = self.width()
            click = pos.x() - handle.width() / 2
            available = slider_len - handle.width()
        else:
            slider_len = self.height()
            click = slider_len - pos.y() - handle.height() / 2
            available = slider_len - handle.height()

        ratio = max(0.0, min(1.0, click / available))
        value = self.minimum() + ratio * (self.maximum() - self.minimum())
        self.setValue(round(value))

    def _handle_rect(self) -> QRect:
        option = QStyleOptionSlider()
        option.initFrom(self)
        option.orientation = self.orientation()
        option.minimum = self.minimum()
        option.maximum = self.maximum()
        option.sliderPosition = self.value()
        option.sliderValue = self.value()
        return self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderHandle,
            self
        )


class MTLineEdit(QLineEdit):
    def __init__(self, *args, obj_name: Optional[str] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name is not None:
            self.setObjectName(obj_name)


class MTSpinBox(QSpinBox):
    def __init__(self, *args, obj_name: Optional[str] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name is not None:
            self.setObjectName(obj_name)

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()
        self.clearFocus()


class MTDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, *args, obj_name: Optional[str] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name is not None:
            self.setObjectName(obj_name)

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()
        self.clearFocus()
                
                
class MTWidget(QWidget):
    def __init__(self, *args, obj_name: Optional[str] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if obj_name is not None:
            self.setObjectName(obj_name)
            