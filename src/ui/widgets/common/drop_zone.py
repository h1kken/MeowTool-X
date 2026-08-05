from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QKeySequence, QMouseEvent, QShortcut
from PySide6.QtWidgets import QApplication, QWidget, QFileDialog

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout

from .label import MTLabel
from .widget import MTWidget


class MTDropZone(MTWidget):
    pathsDropped = Signal(list[Path])
    textDropped = Signal(str)
    
    _OBJECT_NAME = 'DropZone'

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tr_key: str = '',
        obj_name: tuple[str, ...] = (),
        accept_files: bool = True,
        accept_text: bool = True,
        browse_on_click: bool = True,
    ) -> None:
        super().__init__(parent, obj_name=(*obj_name, self._OBJECT_NAME))

        self.setAcceptDrops(accept_files or accept_text)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        if browse_on_click:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._accept_files = accept_files
        self._accept_text = accept_text
        self._browse_on_click = browse_on_click

        self._build_ui(tr_key=tr_key, obj_name=(*obj_name, self._OBJECT_NAME))
        self._connect_signals()

    def _build_ui(
        self,
        *,
        tr_key: str = '',
        obj_name: tuple[str, ...] = (),
    ) -> None:
        self._main_layout = create_layout(LayoutType.VBOX, self)

        self._label = MTLabel(tr_key=tr_key, obj_name=obj_name)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._main_layout.addWidget(self._label)

    def _connect_signals(self) -> None:
        self._paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self._paste_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._paste_shortcut.activated.connect(self._on_paste)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._can_accept_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        
        self.setCursor(Qt.CursorShape.ForbiddenCursor)
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self.unsetCursor()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._process_mime(event.mimeData())
        event.acceptProposedAction()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._browse_on_click:
                self._browse_files()
                event.accept()
                return
        
        super().mouseReleaseEvent(event)

    def _on_paste(self) -> None:
        self._process_mime(QApplication.clipboard().mimeData())

    def _browse_files(self) -> None:
        caption = self._label.text().strip()
        start_dir = str(Path.home())
        selected_paths, _ = QFileDialog.getOpenFileNames(self, caption, start_dir)
        if not selected_paths:
            return

        paths = [path for path in (Path(item) for item in selected_paths) if path.exists()]
        if not paths:
            return
        
        self.pathsDropped.emit(paths)

    def _can_accept_mime(self, mime: QMimeData) -> bool:
        if self._accept_files and mime.hasUrls():
            return True

        if self._accept_text and mime.hasText() and bool(mime.text().strip()):
            return True

        return False

    def _process_mime(self, mime: QMimeData) -> None:
        if self._accept_files and mime.hasUrls():
            dropped_paths = self._extract_paths(mime)
            
            if dropped_paths:
                self.pathsDropped.emit(dropped_paths)
                return

        if self._accept_text and mime.hasText():
            dropped_text = mime.text()
            
            if dropped_text.strip():
                self.textDropped.emit(dropped_text)

    def _extract_paths(self, mime: QMimeData) -> list[Path]:
        files: list[Path] = []
    
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            
            path = Path(url.toLocalFile())
    
            if path.is_file():
                files.append(path)
                continue
            
            if path.is_dir():
                files.extend(item for item in path.rglob('*') if item.is_file())
    
        return files
