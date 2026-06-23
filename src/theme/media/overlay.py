from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from src.ui.widgets.custom.media import MTMediaWidget


class ThemeMediaOverlay(MTMediaWidget):
    def __init__(self, parent: QWidget):
        super().__init__(
            parent=parent,
            obj_name='Theme_Media_Overlay',
            image_obj_name='Theme_Media_Overlay_Image_Label',
            video_obj_name='Theme_Media_Overlay_Video_Widget',
            content_margins=0,
            transparent_for_mouse=True,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

    def reset_theme(self) -> None:
        super().reset_theme()
        self.hide()

    def apply_theme(self, data: dict[str, Any]) -> None:
        self.apply_media_theme(data)
        self.setVisible(self.has_media())

    def sync_geometry(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return

        self.setGeometry(parent.rect())
        self._refresh_visuals()
        if parent.isVisible() and self.has_media():
            self.show()
            self.lower()
        else:
            self.hide()
