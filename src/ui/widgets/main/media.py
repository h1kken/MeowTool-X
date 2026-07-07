from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QObject, QSize, Qt, QUrl
from PySide6.QtGui import QMovie, QPixmap, QResizeEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from src.app.paths import PATH_APP_ICON, PATH_ROOT
from src.ui.constants import (
    SIDEBAR_MEDIA_GIF_EXTENSIONS,
    SIDEBAR_MEDIA_HEIGHT,
    SIDEBAR_MEDIA_IMAGE_EXTENSIONS,
    SIDEBAR_MEDIA_MARGIN,
    SIDEBAR_MEDIA_VIDEO_EXTENSIONS,
)
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets.main.containers import MTWidget
from src.ui.widgets.main.text import MTLabel

_MEDIA_FIT_CONTAIN = 'contain'
_MEDIA_FIT_COVER = 'cover'
_MEDIA_FIT_STRETCH = 'stretch'
_MEDIA_FIT_CENTER = 'center'
_DEFAULT_MEDIA_FIT = _MEDIA_FIT_CONTAIN


class MTVideoWidget(QVideoWidget):
    def __init__(self, parent: QWidget | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if obj_name:
            self.setObjectName(obj_name)


class MTAudioOutput(QAudioOutput):
    def __init__(self, parent: QObject | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent)
        if obj_name:
            self.setObjectName(obj_name)


class MTMediaPlayer(QMediaPlayer):
    def __init__(self, parent: QObject | None = None, *, obj_name: str = '') -> None:
        super().__init__(parent)
        if obj_name:
            self.setObjectName(obj_name)


class MTMediaWidget(MTWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: str = '',
        image_obj_name: str = '',
        video_obj_name: str = '',
        content_margins: int | tuple[int, int, int, int] = SIDEBAR_MEDIA_MARGIN,
        transparent_for_mouse: bool = False,
    ) -> None:
        super().__init__(parent=parent, obj_name=obj_name)
        self._source_pixmap = QPixmap()
        self._current_path: Path | None = None
        self._movie: QMovie | None = None
        self._video_widget: MTVideoWidget | None = None
        self._audio_output: MTAudioOutput | None = None
        self._media_player: MTMediaPlayer | None = None
        self._source = ''
        self._fit = _DEFAULT_MEDIA_FIT
        if isinstance(content_margins, tuple) and len(content_margins) == 4:
            self._content_margins: tuple[int, int, int, int] = (
                int(max(0, content_margins[0])),
                int(max(0, content_margins[1])),
                int(max(0, content_margins[2])),
                int(max(0, content_margins[3])),
            )
        else:
            margin = max(0, int(content_margins))
            self._content_margins = (margin, margin, margin, margin)
        self._transparent_for_mouse = bool(transparent_for_mouse)
        self._image_obj_name = image_obj_name
        self._video_obj_name = video_obj_name

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        if self._transparent_for_mouse:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._layout: QVBoxLayout = create_layout(
            LayoutType.VBOX,
            parent=self,
            margins=self._content_margins,
            spacing=0,
        )

        self._image_label = MTLabel(
            tr_key='',
            parent=self,
            obj_name=self._image_obj_name or self._child_obj_name('Image_Label', 'Media_Image_Label'),
        )
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        if self._transparent_for_mouse:
            self._image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._layout.addWidget(self._image_label)

        self._show_image_area()
        self.reset_theme()

    def has_media(self) -> bool:
        return self._current_path is not None

    def reset_theme(self) -> None:
        self._source = ''
        self._fit = _DEFAULT_MEDIA_FIT
        self._clear_media_layer()

    def apply_media_theme(self, data: dict[str, Any]) -> None:
        source = ''
        direct_source = data.get('source')
        if isinstance(direct_source, str) and direct_source.strip():
            source = direct_source.strip()
        else:
            icon_data = data.get('icon')
            if isinstance(icon_data, dict):
                icon_source = cast(dict[str, Any], icon_data).get('source')
                if isinstance(icon_source, str) and icon_source.strip():
                    source = icon_source.strip()
        if source or 'source' in data or isinstance(data.get('icon'), dict):
            self._source = source
        if 'fit' in data:
            token = str(data.get('fit') or '').strip().lower()
            if token in (_MEDIA_FIT_CONTAIN, ''):
                self._fit = _MEDIA_FIT_CONTAIN
            elif token == _MEDIA_FIT_COVER:
                self._fit = _MEDIA_FIT_COVER
            elif token in (_MEDIA_FIT_STRETCH, 'fill'):
                self._fit = _MEDIA_FIT_STRETCH
            elif token in (_MEDIA_FIT_CENTER, 'free'):
                self._fit = _MEDIA_FIT_CENTER
            else:
                self._fit = _DEFAULT_MEDIA_FIT

        self._apply_current_media()

    def set_source(self, source: str | Path | None) -> None:
        self._source = str(source).strip() if source is not None else ''
        self._apply_current_media()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_visuals()

    def _apply_current_media(self) -> None:
        if not self._source:
            path = None
        else:
            candidate = Path(self._source).expanduser()
            candidates = [candidate]
            if not candidate.is_absolute():
                candidates.append(PATH_ROOT / candidate)
            path = next((item for item in candidates if item.exists() and item.is_file()), None)
        if path is None:
            self._clear_media_layer()
            return

        suffix = path.suffix.lower()
        if suffix in SIDEBAR_MEDIA_GIF_EXTENSIONS:
            if not self._set_gif(path):
                self._clear_media_layer()
                return
        elif suffix in SIDEBAR_MEDIA_VIDEO_EXTENSIONS:
            self._set_video(path)
        elif suffix in SIDEBAR_MEDIA_IMAGE_EXTENSIONS:
            if not self._set_image(path):
                self._clear_media_layer()
                return
        else:
            self._clear_media_layer()
            return

        self.show()

    def _set_image(self, path: Path) -> bool:
        self._clear_media()
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return False

        self._source_pixmap = pixmap
        self._current_path = path
        self._show_image_area()
        self._refresh_visuals()
        return True

    def _set_gif(self, path: Path) -> bool:
        self._clear_media()
        movie = QMovie(str(path))
        if not movie.isValid():
            movie.deleteLater()
            return False

        self._movie = movie
        self._current_path = path
        self._show_image_area()
        self._image_label.setMovie(movie)
        self._refresh_movie_scale()
        movie.start()
        return True

    def _set_video(self, path: Path) -> None:
        self._clear_media()
        self._ensure_video_stack()
        self._current_path = path
        self._image_label.hide()
        if self._video_widget is not None:
            self._video_widget.show()
            self._video_widget.setAspectRatioMode(self._video_aspect_mode())
        if self._media_player is not None:
            self._media_player.setSource(QUrl.fromLocalFile(str(path.resolve())))
            self._media_player.play()

    def _clear_media(self) -> None:
        if self._media_player is not None:
            self._media_player.stop()
            self._media_player.setSource(QUrl())

        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None

        self._source_pixmap = QPixmap()
        self._image_label.clear()
        self._current_path = None

    def _clear_media_layer(self) -> None:
        self._clear_media()
        self._show_image_area()
        self.show()

    def _show_image_area(self) -> None:
        if self._video_widget is not None:
            self._video_widget.hide()
        self._image_label.show()

    def _ensure_video_stack(self) -> None:
        if self._video_widget is not None and self._audio_output is not None and self._media_player is not None:
            return

        self._video_widget = MTVideoWidget(
            self,
            obj_name=self._video_obj_name or self._child_obj_name('Video_Widget', 'Media_Video_Widget'),
        )
        if self._transparent_for_mouse:
            self._video_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._video_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._video_widget.hide()
        self._layout.addWidget(self._video_widget)

        self._audio_output = MTAudioOutput(
            self,
            obj_name=self._child_obj_name('Audio_Output', 'Media_Audio_Output'),
        )
        self._audio_output.setMuted(True)
        self._audio_output.setVolume(0.0)

        self._media_player = MTMediaPlayer(
            self,
            obj_name=self._child_obj_name('Media_Player', 'Media_Player'),
        )
        self._media_player.setAudioOutput(self._audio_output)
        self._media_player.setVideoOutput(self._video_widget)
        self._media_player.setLoops(-1)

    def _target_media_size(self) -> QSize:
        left, top, right, bottom = self._content_margins
        width = max(1, self.width() - left - right)
        height = max(1, self.height() - top - bottom)
        return QSize(width, height)

    def _video_aspect_mode(self) -> Qt.AspectRatioMode:
        if self._fit == _MEDIA_FIT_STRETCH:
            return Qt.AspectRatioMode.IgnoreAspectRatio
        if self._fit == _MEDIA_FIT_COVER:
            return Qt.AspectRatioMode.KeepAspectRatioByExpanding
        return Qt.AspectRatioMode.KeepAspectRatio

    def _refresh_movie_scale(self) -> None:
        if self._movie is None:
            return
        if self._fit == _MEDIA_FIT_CENTER:
            return
        self._movie.setScaledSize(self._target_media_size())

    def _refresh_visuals(self) -> None:
        target_size = self._target_media_size()
        if self._movie is not None:
            self._refresh_movie_scale()
            return

        if self._video_widget is not None:
            self._video_widget.setAspectRatioMode(self._video_aspect_mode())
            return

        if self._source_pixmap.isNull():
            return

        if self._fit == _MEDIA_FIT_CENTER:
            pixmap = self._source_pixmap
        elif self._fit == _MEDIA_FIT_STRETCH:
            pixmap = self._source_pixmap.scaled(
                target_size,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        elif self._fit == _MEDIA_FIT_COVER:
            pixmap = self._source_pixmap.scaled(
                target_size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            pixmap = self._source_pixmap.scaled(
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._image_label.setPixmap(pixmap)

    def _child_obj_name(self, suffix: str, fallback: str) -> str:
        base = self.objectName().strip()
        return f'{base}_{suffix}' if base else fallback


class SidebarMediaWidget(MTMediaWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent=parent,
            obj_name='Sidebar_Media_Widget',
            image_obj_name='Sidebar_Media_Image_Label',
            video_obj_name='Sidebar_Media_Video_Widget',
            content_margins=SIDEBAR_MEDIA_MARGIN,
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(SIDEBAR_MEDIA_HEIGHT)
        self.setMaximumHeight(SIDEBAR_MEDIA_HEIGHT)
        self._layout.setAlignment(self._image_label, Qt.AlignmentFlag.AlignCenter)

    def reset_theme(self) -> None:
        super().reset_theme()
        self._source = str(PATH_APP_ICON) if PATH_APP_ICON.is_file() else ''
        self._apply_current_media()

    def _apply_current_media(self) -> None:
        super()._apply_current_media()
        self.setVisible(self._current_path is not None)
