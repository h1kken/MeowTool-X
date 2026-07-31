from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, QUrl, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent,  QKeySequence, QMouseEvent,  QShortcut
from PySide6.QtWidgets import QApplication, QFileDialog

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets import MTLabel, MTWidget


class MTDropZone(MTWidget):
    filesDropped = Signal(list)
    textDropped = Signal(str)

    def __init__(
        self,
        *,
        tr_key: str = '',
        obj_name: str = '',
        accept_files: bool = True,
        accept_text: bool = True,
    ) -> None:
        super().__init__(obj_name=f'{obj_name}_Drop_Zone' if obj_name else '')

        self._accept_files = bool(accept_files)
        self._accept_text = bool(accept_text)

        self.setAcceptDrops(self._accept_files or self._accept_text)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if self._accept_files:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = create_layout(LayoutType.VBOX, self)

        self._title_label = MTLabel(tr_key=tr_key, obj_name=f'{obj_name}_Drop_Zone_Title' if obj_name else '')
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._title_label)

        self._paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self._paste_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._paste_shortcut.activated.connect(self._on_paste_shortcut)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._can_accept_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if self._process_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            if self._accept_files:
                self._browse_files()
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def _on_paste_shortcut(self) -> None:
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        self._process_mime(mime)

    def _browse_files(self) -> None:
        caption = self._title_label.text().strip() or 'Select files'
        start_dir = str(Path.home())
        selected_paths, _ = QFileDialog.getOpenFileNames(self, caption, start_dir)
        if not selected_paths:
            return

        paths = [path for path in (Path(item) for item in selected_paths) if path.exists()]
        if not paths:
            return
        self.filesDropped.emit(paths)

    def _can_accept_mime(self, mime: QMimeData | None) -> bool:
        if mime is None:
            return False

        if self._accept_files:
            if mime.hasUrls():
                return True
            if mime.hasText() and bool(self._extract_paths_from_text(mime.text())):
                return True

        if self._accept_text and mime.hasText() and bool(mime.text().strip()):
            return True

        return False

    def _process_mime(self, mime: QMimeData | None) -> bool:
        if mime is None:
            return False

        accepted = False
        dropped_paths: list[Path] = []

        if self._accept_files:
            dropped_paths = self._extract_paths(mime)
            if dropped_paths:
                self.filesDropped.emit(dropped_paths)
                accepted = True

        if self._accept_text and mime.hasText():
            text = mime.text().strip()
            skip_as_text = self._accept_files and (
                self._looks_like_uri_dump(text) or self._looks_like_paths_dump(text)
            )
            if text and not skip_as_text:
                self.textDropped.emit(text)
                accepted = True

        return accepted

    def _extract_paths(self, mime: QMimeData) -> list[Path]:
        urls_paths = self._extract_paths_from_urls(mime)
        if urls_paths:
            return urls_paths

        if mime.hasText():
            return self._extract_paths_from_text(mime.text())

        return []

    def _extract_paths_from_urls(self, mime: QMimeData) -> list[Path]:
        paths: list[Path] = []
        seen: set[str] = set()

        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if not path.exists():
                continue

            key = self._path_key(path)
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)

        return paths

    def _extract_paths_from_text(self, text: str) -> list[Path]:
        paths: list[Path] = []
        seen: set[str] = set()

        for line in text.splitlines():
            path = self._line_to_existing_path(line)
            if path is None:
                continue

            key = self._path_key(path)
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)

        return paths

    def _line_to_existing_path(self, line: str) -> Path | None:
        candidate = line.strip().strip('"')
        if not candidate:
            return

        path: Path | None = None
        if candidate.lower().startswith('file://'):
            url = QUrl(candidate)
            if url.isLocalFile():
                path = Path(url.toLocalFile())
        else:
            path = Path(candidate)

        if path is None or not path.exists():
            return
        return path

    def _looks_like_uri_dump(self, text: str) -> bool:
        lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
        if not lines:
            return False
        return all(line.startswith('file://') for line in lines)

    def _looks_like_paths_dump(self, text: str) -> bool:
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return False
        return all(self._line_to_existing_path(line) is not None for line in lines)

    def _path_key(self, path: Path) -> str:
        try:
            return str(path.resolve()).lower()
        except OSError:
            return str(path.absolute()).lower()
