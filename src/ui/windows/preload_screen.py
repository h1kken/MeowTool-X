from __future__ import annotations

from time import monotonic
from typing import Any

from PySide6.QtCore import QEvent, QPoint, QSize, Qt
from PySide6.QtGui import QFont, QFontMetricsF, QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from src.theme.manager import ThemeManager
from src.translation import translator as t
from src.ui.layouts.factory import LayoutType, create_layout
from src.ui.widgets import MTLabel
from src.ui.windows.preload_widgets import StartupRingWidget, _PreloadWindowFrame
from src.utils.preload import (
    build_preload_surface_theme_payload,
    build_preload_theme_payload,
    format_preload_counter_remaining,
    format_preload_counter_with_label,
    resolve_preload_target_styles,
    split_preload_stage_text,
)

from src.utils.constants import (
    PATH_APP_ICON,
    PATH_APP_LABEL,
    PRELOAD_BRAND_HEIGHT_RATIO,
    PRELOAD_BRAND_MIN_HEIGHT,
    PRELOAD_BRAND_MIN_WIDTH,
    PRELOAD_BRAND_TARGET_MIN_WIDTH,
    PRELOAD_BRAND_WIDTH_RATIO,
    PRELOAD_COUNT_FONT_SIZE,
    PRELOAD_DEFAULT_COUNTER,
    PRELOAD_DEFAULT_STAGE,
    PRELOAD_DEFAULT_STATUS,
    PRELOAD_DEFAULT_SUBTITLE,
    PRELOAD_DRAG_FLUSH_FPS,
    PRELOAD_FLUSH_FPS,
    PRELOAD_LAYOUT_MARGINS,
    PRELOAD_MIDDLE_SPACING,
    PRELOAD_RING_SPACING,
    PRELOAD_STATUS_FONT_SIZE,
    PRELOAD_SUBTITLE_FONT_SIZE,
    PRELOAD_TITLE_FONT_SIZE,
    PRELOAD_TOP_SPACING,
    PRELOAD_WINDOW_HEIGHT,
    PRELOAD_WINDOW_WIDTH,
    PROGRAM_NAME,
)


class PreloadScreen(_PreloadWindowFrame):
    def __init__(self, *, theme: dict[str, Any] | None = None) -> None:
        super().__init__(parent=None)
        self._program_name = PROGRAM_NAME
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.Tool, False)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self.setAutoFillBackground(False)
        self.setWindowTitle(self._program_name)
        self._theme_fixed_height = None
        self._theme_min_height = None
        self._theme_max_height = None
        self._theme: dict[str, Any] = {}
        self._window_styles: dict[str, Any] = {}
        self._surface_theme: dict[str, Any] = {}
        self._drag_active = False
        self._drag_offset = QPoint()
        self._last_flush_at = 0.0
        self._has_been_shown = False
        self._brand_pixmap = QPixmap(str(PATH_APP_LABEL)) if PATH_APP_LABEL.exists() else QPixmap()
        self._current_stage = PRELOAD_DEFAULT_STAGE
        self._current_step = 0.0
        self._current_total = 0.0
        self._current_counter_text: str | None = None

        self._root_layout = create_layout(LayoutType.VBOX, parent=self)
        self._theme_manager = ThemeManager(self, emit_theme_changed=False)

        layout = self._root_layout

        self._title_image_label = MTLabel(self, tr_key='', obj_name='Preload_Title_Image')
        self._title_image_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._title_image_label.setVisible(False)
        layout.addSpacing(PRELOAD_TOP_SPACING)
        layout.addWidget(self._title_image_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Title
        self._title_label = self._create_center_label(
            self._program_name,
            obj_name='Preload_Title',
            point_size=PRELOAD_TITLE_FONT_SIZE,
            min_point_size=12.0,
            bold=True,
        )
        layout.addWidget(self._title_label)

        layout.addSpacing(PRELOAD_MIDDLE_SPACING)

        # Ring
        self._ring = StartupRingWidget(image_path=PATH_APP_ICON, parent=self)
        layout.addWidget(self._ring, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(PRELOAD_RING_SPACING)

        self._status_label = self._create_center_label(
            PRELOAD_DEFAULT_STATUS,
            obj_name='Preload_Status',
            point_size=PRELOAD_STATUS_FONT_SIZE,
            min_point_size=7.0,
            bold=True,
        )
        layout.addWidget(self._status_label)

        # Subtitle
        self._subtitle_label = self._create_center_label(
            PRELOAD_DEFAULT_SUBTITLE,
            obj_name='Preload_Subtitle',
            point_size=PRELOAD_SUBTITLE_FONT_SIZE,
            min_point_size=7.0,
        )
        self._subtitle_label.setVisible(False)
        layout.addWidget(self._subtitle_label)

        # Counter
        self._count_label = self._create_center_label(
            PRELOAD_DEFAULT_COUNTER,
            obj_name='Preload_Count',
            point_size=PRELOAD_COUNT_FONT_SIZE,
            min_point_size=7.0,
        )
        layout.addWidget(self._count_label)

        for widget in (self, *self.findChildren(QWidget)):
            widget.installEventFilter(self)
        t.language_changed.connect(self._retranslate_runtime_texts)
        self.apply_theme(theme)
        self._retranslate_runtime_texts()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._has_been_shown = True
        self._update_brand_image()
        self._rescale_text_labels()
        self._fit_to_content_height()
        self._center_on_screen()
        self.setWindowOpacity(1.0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_brand_image()
        self._rescale_text_labels()

    def prepare_startup(
        self,
        *,
        total: int | float,
        stage: str = PRELOAD_DEFAULT_STAGE,
        counter_text: str | None = None,
    ) -> None:
        if not self.isVisible():
            self.show()

        self.ensurePolished()
        self.update_progress(
            0,
            total,
            stage,
            counter_text=counter_text or format_preload_counter_with_label(0, total, 'PRELOAD_COUNTER_LABEL_STARTUP'),
        )
        self._flush_display(force=True)

    def update_progress(
        self,
        step: int | float,
        total: int | float,
        stage: str,
        counter_text: str | None = None,
    ) -> None:
        safe_total = max(1.0, float(total))
        safe_step = max(0.0, min(float(step), safe_total))
        percent = (safe_step / safe_total) * 100.0

        self._current_stage = stage
        self._current_step = safe_step
        self._current_total = safe_total
        self._current_counter_text = counter_text.strip() if isinstance(counter_text, str) and counter_text.strip() else None

        self._ring.set_progress(percent)
        self._retranslate_runtime_texts()
        self._rescale_text_labels()
        self._flush_display(force=safe_step >= safe_total)

    def apply_theme(self, theme: dict[str, Any] | None) -> None:
        raw_theme = theme if isinstance(theme, dict) else {}
        self._theme = build_preload_theme_payload(raw_theme)
        self._window_styles = resolve_preload_target_styles(raw_theme, 'Preload_Window')
        self._surface_theme = build_preload_surface_theme_payload(raw_theme)
        self.setWindowTitle(self._program_name)
        self._title_label.setText(self._program_name)

        self._apply_window_geometry_theme(self._window_styles)
        self.apply_frame_theme(self._window_styles)
        self._theme_manager.load(self._surface_theme)
        self._theme_manager.apply()
        self._sync_surface_frame_inset()
        self._update_brand_image()
        self._rescale_text_labels()
        self._fit_to_content_height()

    def apply_runtime_theme_preferences(self, enabled: bool, duration_ms: int, palette: str = 'Pastel') -> None:
        self._ring.set_progress_rainbow(bool(enabled), int(duration_ms), palette=palette)


    def _retranslate_runtime_texts(self) -> None:
        action_text, target_text = split_preload_stage_text(self._current_stage)
        self._status_label.setText(action_text or PRELOAD_DEFAULT_STATUS)
        self._subtitle_label.setText(target_text or PRELOAD_DEFAULT_SUBTITLE)
        self._subtitle_label.setVisible(bool(target_text))
        if isinstance(self._current_counter_text, str) and self._current_counter_text.strip():
            self._count_label.setText(self._current_counter_text.strip())
        elif self._current_total > 0.0:
            self._count_label.setText(format_preload_counter_remaining(self._current_step, self._current_total))
        else:
            self._count_label.setText(PRELOAD_DEFAULT_COUNTER)
        self._rescale_text_labels()
        self._fit_to_content_height()

    def _sync_surface_frame_inset(self) -> None:
        window_styles = resolve_preload_target_styles(self._theme, 'Preload_Window')
        inset = self._resolve_window_frame_inset(window_styles)
        self._root_layout.setContentsMargins(inset, inset, inset, inset)

    def _apply_window_geometry_theme(self, styles: dict[str, Any]) -> None:
        geometry = styles.get('geometry') if isinstance(styles.get('geometry'), dict) else {}
        width = self._parse_px_measure(
            geometry.get('fixed_width', geometry.get('width')) if isinstance(geometry, dict) else None
        )
        if width is not None and width > 0.0:
            self.setFixedWidth(max(1, int(round(width))))

        fixed_height = self._parse_px_measure(
            geometry.get('fixed_height', geometry.get('height')) if isinstance(geometry, dict) else None
        )
        min_height = self._parse_px_measure(geometry.get('min_height')) if isinstance(geometry, dict) else None
        max_height = self._parse_px_measure(geometry.get('max_height')) if isinstance(geometry, dict) else None

        self._theme_fixed_height = max(1, int(round(fixed_height))) if fixed_height is not None and fixed_height > 0.0 else None
        self._theme_min_height = max(1, int(round(min_height))) if min_height is not None and min_height > 0.0 else None
        self._theme_max_height = max(1, int(round(max_height))) if max_height is not None and max_height > 0.0 else None

        if (
            self._theme_min_height is not None
            and self._theme_max_height is not None
            and self._theme_min_height > self._theme_max_height
        ):
            self._theme_min_height, self._theme_max_height = self._theme_max_height, self._theme_min_height

    def _resolve_window_frame_inset(self, styles: dict[str, Any]) -> int:
        if not isinstance(styles, dict):
            return 0

        border = styles.get('border') if isinstance(styles.get('border'), dict) else {}
        background = styles.get('background') if isinstance(styles.get('background'), dict) else {}
        layout = styles.get('layout') if isinstance(styles.get('layout'), dict) else {}

        inset = 0

        border_width = self._parse_px_measure(border.get('width'))
        if border_width is not None:
            inset = max(inset, max(1, int(round(border_width))))

        padding = styles.get('padding')
        if padding is None and isinstance((content := styles.get('content')), dict):
            padding = content.get('padding')
        if isinstance(padding, (list, tuple)) and padding:
            try:
                inset = max(inset, max(int(float(value)) for value in padding))
            except (TypeError, ValueError):
                pass
        elif isinstance(padding, str):
            if (padding_value := self._parse_px_measure(padding)) is not None:
                inset = max(inset, int(round(padding_value)))

        margins = layout.get('margin', layout.get('margins'))
        if isinstance(margins, (list, tuple)) and margins:
            try:
                inset = max(inset, max(int(float(value)) for value in margins))
            except (TypeError, ValueError):
                pass

        if inset == 0 and (background or border):
            inset = 1

        return max(0, inset)

    def _parse_px_measure(self, value: Any) -> float | None:
        if value is None:
            return None
        text = str(value).strip().lower()
        if not text:
            return None
        if text.endswith('px'):
            text = text[:-2].strip()
        if text.endswith('%'):
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _create_center_label(
        self,
        text: str = '',
        *,
        obj_name: str,
        point_size: float,
        min_point_size: float,
        bold: bool = False,
        tr_key: str | None = None,
    ) -> MTLabel:
        label = MTLabel(self, tr_key='', obj_name=obj_name)
        label.setText(t.tr(tr_key) if isinstance(tr_key, str) and tr_key.strip() else text)
        font = QFont(self.font())
        font.setPointSizeF(float(point_size))
        font.setBold(bool(bold))
        label.setFont(font)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._configure_scaling_label(label, base_point_size=float(point_size), min_point_size=float(min_point_size))
        return label

    def _configure_scaling_label(
        self,
        label: MTLabel,
        *,
        base_point_size: float,
        min_point_size: float,
    ) -> None:
        label.setWordWrap(False)
        label.setProperty('_basePointSize', float(base_point_size))
        label.setProperty('_minPointSize', float(min_point_size))
        stable_font = QFont(label.font())
        stable_font.setPointSizeF(float(base_point_size))
        stable_height = max(1, int(QFontMetricsF(stable_font).height() + 6.0))
        label.setFixedHeight(stable_height)

    def _rescale_text_labels(self) -> None:
        for label in (
            self._title_label,
            self._status_label,
            self._subtitle_label,
            self._count_label,
        ):
            self._fit_label_text(label)

    def _update_brand_image(self) -> None:
        if self._brand_pixmap.isNull():
            self._title_image_label.clear()
            self._title_image_label.setVisible(False)
            self._title_label.setVisible(True)
            return

        available_width = max(PRELOAD_BRAND_MIN_WIDTH, self.width() - (PRELOAD_LAYOUT_MARGINS * 2))
        target_width = min(available_width, max(PRELOAD_BRAND_TARGET_MIN_WIDTH, int(self.width() * PRELOAD_BRAND_WIDTH_RATIO)))
        base_height = self._theme_fixed_height or self.height() or PRELOAD_WINDOW_HEIGHT
        max_height = max(PRELOAD_BRAND_MIN_HEIGHT, int(base_height * PRELOAD_BRAND_HEIGHT_RATIO))
        scaled = self._brand_pixmap.scaled(
            target_width,
            max_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._title_image_label.setPixmap(scaled)
        self._title_image_label.setFixedSize(scaled.size())
        self._title_image_label.setVisible(True)
        self._title_label.setVisible(False)

    def _fit_label_text(self, label: MTLabel) -> None:
        text = label.text().strip()
        if not text:
            return

        base_point_size = float(label.property('_basePointSize') or label.font().pointSizeF() or 10.0)
        min_point_size = float(label.property('_minPointSize') or min(base_point_size, 7.0))
        available_width = max(1.0, float(label.contentsRect().width()) - 4.0)

        template_font = QFont(label.font())
        chosen_size = min_point_size

        test_font = QFont(template_font)
        test_font.setPointSizeF(min_point_size)
        if QFontMetricsF(test_font).horizontalAdvance(text) <= available_width:
            low = min_point_size
            high = max(min_point_size, base_point_size)
            for _ in range(12):
                mid = (low + high) / 2.0
                probe_font = QFont(template_font)
                probe_font.setPointSizeF(mid)
                if QFontMetricsF(probe_font).horizontalAdvance(text) <= available_width:
                    chosen_size = mid
                    low = mid
                else:
                    high = mid

        fitted_font = QFont(template_font)
        fitted_font.setPointSizeF(chosen_size)
        label.setFont(fitted_font)

    def _fit_to_content_height(self) -> None:
        if not self._has_been_shown and not self.isVisible():
            return
        self._root_layout.activate()

        hint = self.sizeHint()
        minimum = self.minimumSizeHint()
        target_height = max(1, int(hint.height()), int(minimum.height()))
        if self._theme_fixed_height is not None:
            target_height = self._theme_fixed_height
        else:
            if self._theme_min_height is not None:
                target_height = max(target_height, self._theme_min_height)
            if self._theme_max_height is not None:
                target_height = min(target_height, self._theme_max_height)
        if self.height() != target_height:
            self.setFixedSize(QSize(max(1, self.width()), target_height))

    def _center_on_screen(self) -> None:
        if (screen := self.screen()) is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return

        geometry = screen.availableGeometry()
        x = geometry.x() + ((geometry.width() - self.width()) // 2)
        y = geometry.y() + ((geometry.height() - self.height()) // 2)
        self.move(x, y)

    def _flush_display(self, *, force: bool = False) -> None:
        self.update()
        self._ring.update()

        now = monotonic()
        min_interval = 1.0 / (PRELOAD_DRAG_FLUSH_FPS if self._drag_active else PRELOAD_FLUSH_FPS)
        if not force and (now - self._last_flush_at) < min_interval:
            return

        self._last_flush_at = now
        QApplication.processEvents()

    def eventFilter(self, obj, event: QEvent) -> bool:
        if isinstance(obj, QWidget) and self._is_drag_event(event):
            return self._handle_drag_event(event)
        return super().eventFilter(obj, event)

    def _is_drag_event(self, event: QEvent) -> bool:
        return event.type() in {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonRelease,
        }

    def _handle_drag_event(self, event) -> bool:
        if not isinstance(event, QMouseEvent):
            return False

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            self._drag_active = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return True

        if event.type() == QEvent.Type.MouseMove:
            if not self._drag_active or not (event.buttons() & Qt.MouseButton.LeftButton):
                return False
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return True

        if event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            self._drag_active = False
            self._flush_display(force=True)
            event.accept()
            return True

        return False

