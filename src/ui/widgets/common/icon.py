from functools import lru_cache

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QTransform, QPaintEvent
from PySide6.QtWidgets import QWidget

from src.utils.qt import build_object_name

from .widget import MTWidget


class MTIcon(MTWidget):
    _OBJECT_NAME = 'Icon'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
        source: str = '',
        color: str | None = None,
        rotation: float = 0.0,
        size: int = 16,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setObjectName(build_object_name((*obj_name, self._OBJECT_NAME)))

        self._source = source
        self._color = color
        self._rotation = rotation
        self._size = max(1, int(size))

        self._pixmap = QPixmap()

        self._update_pixmap()

    @property
    def source(self) -> str:
        return self._source

    @property
    def color(self) -> str | None:
        return self._color

    @property
    def rotation(self) -> float:
        return self._rotation

    def setSource(self, source: str) -> None:
        if self._source == source:
            return

        self._source = source
        self._update_pixmap()

    def setColor(self, color: str | None) -> None:
        if self._color == color:
            return

        self._color = color
        self._update_pixmap()

    def setRotation(self, rotation: float) -> None:
        if self._rotation == rotation:
            return

        self._rotation = rotation
        self._update_pixmap()

    def setIconSize(self, size: int) -> None:
        size = max(1, int(size))
        if self._size == size:
            return

        self._size = size
        self._update_pixmap()

    def sizeHint(self) -> QSize:
        return QSize(self._size, self._size)

    def paintEvent(self, _event: QPaintEvent) -> None:
        if self._pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        x = (self.width() - self._pixmap.width()) // 2
        y = (self.height() - self._pixmap.height()) // 2

        painter.drawPixmap(x, y, self._pixmap)

    def _update_pixmap(self) -> None:
        if not self._source:
            self._pixmap = QPixmap()
            self.update()
            return

        color = (
            self._color
            if self._color is not None
            else self.palette().windowText().color().name(QColor.NameFormat.HexArgb)
        )

        self._pixmap = self._build_pixmap(self._source, color, self._rotation, self._size,)

        self.setFixedSize(self._size, self._size)
        self.update()

    @staticmethod
    @lru_cache(maxsize=128)
    def _load_pixmap(
        source: str,
        w: int = 16,
        h: int = 16
    ) -> QPixmap:
        return QIcon(source).pixmap(QSize(w, h))

    @staticmethod
    @lru_cache(maxsize=256)
    def _build_pixmap(
        source: str,
        color_name: str,
        rotation: float,
        w: int = 16,
        h: int = 16,
    ) -> QPixmap:
        base = MTIcon._load_pixmap(source, w, h)
        if base.isNull():
            return QPixmap()

        pixmap = QPixmap(base.size())
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.drawPixmap(0, 0, base)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color_name))
        painter.end()

        if rotation:
            pixmap = pixmap.transformed(
                QTransform().rotate(rotation),
                Qt.TransformationMode.SmoothTransformation,
            )

        return pixmap
