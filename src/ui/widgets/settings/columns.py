from __future__ import annotations

import typing as t

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.ui.layouts.enums import LayoutType
from src.ui.layouts.factory import create_layout
from src.ui.widgets.common import MTScrollArea, MTCollapsibleContainer, MTWidget


_SETTING_ROW_GAP = 0
_COLUMN_REBALANCE_EVENT_TYPES = {
    QEvent.Type.Show,
    QEvent.Type.Hide,
}


class MTColumnsSetting(MTScrollArea):
    _OBJECT_NAME = 'Columns'
    
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        obj_name: tuple[str, ...] = (),
        tabs: t.Sequence[QWidget] | None = None,
        columns: int = 2,
    ) -> None:
        self._tabs: list[QWidget] = []
        super().__init__(parent, obj_name=(*obj_name, self._OBJECT_NAME))
        
        self._rebalancing = False

        self._columns = max(1, int(columns))
        self._layouts: list[QVBoxLayout] = []
        self._column_heights: list[int] = [0 for _ in range(self._columns)]
        self._column_assignments: tuple[tuple[int, ...], ...] = tuple(tuple() for _ in range(self._columns))

        self._build_ui(tabs=tabs)
        self._connect_signals()
        
        self._rebalance_columns()

    def _build_ui(
        self,
        *,
        tabs: t.Sequence[QWidget] | None = None,
    ) -> None:
        obj_name = self.objectName()
        
        self._scroll_area_content = MTWidget(obj_name=(obj_name, 'Content'))
        self._main_layout = create_layout(LayoutType.HBOX, parent=self._scroll_area_content)
        self.setWidget(self._scroll_area_content)

        for index in range(self._columns):
            column_widget = MTWidget(obj_name=(obj_name, str(index), 'Column'))
            column_layout = create_layout(LayoutType.VBOX, column_widget)
            self._main_layout.addWidget(column_widget, stretch=1)
            self._layouts.append(column_layout)

        for layout in self._layouts:
            layout.addStretch()

        if tabs is not None:
            for tab in tabs:
                self.add_tab(tab)

    def _connect_signals(self) -> None:
        self._rebalance_timer = QTimer(self, singleShot=True, interval=0)
        self._rebalance_timer.timeout.connect(self._rebalance_columns)

    def add_tab(self, tab: QWidget) -> None:
        self._tabs.append(tab)
        self._attach_tab_observers(tab)
        self.request_rebalance()

    def request_rebalance(self) -> None:
        if self._rebalancing:
            return
        self._rebalance_timer.start()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched in self._tabs and event.type() in _COLUMN_REBALANCE_EVENT_TYPES:
            self.request_rebalance()
        return super().eventFilter(watched, event)

    def _rebalance_columns(self) -> None:
        if self._rebalancing:
            return

        self._rebalance_timer.stop()
        self._rebalancing = True
        try:
            self._prepare_tabs_for_measurement()
            assignments, heights = self._build_column_plan()
            if assignments != self._column_assignments:
                self._apply_column_plan(assignments)
            self._column_heights = heights

            self._scroll_area_content.updateGeometry()
            scroll_widget = self.widget()
            if scroll_widget is not None:
                scroll_widget.updateGeometry()
            self.updateGeometry()
        finally:
            self._rebalancing = False

    def _attach_tab_observers(self, tab: QWidget) -> None:
        tab.installEventFilter(self)
        if not isinstance(tab, MTCollapsibleContainer):
            return
        tab.toggled.connect(self._on_tab_toggled)

    def _on_tab_toggled(self, *_args: object) -> None:
        self.request_rebalance()

    def _target_column_index(self) -> int:
        return min(
            range(len(self._column_heights)),
            key=lambda index: self._column_heights[index],
        )

    def _build_column_plan(self) -> tuple[tuple[tuple[int, ...], ...], list[int]]:
        self._column_heights = [0 for _ in range(self._columns)]
        columns: list[list[int]] = [[] for _ in range(self._columns)]

        for tab_index, tab in enumerate(self._tabs):
            column_index = self._target_column_index()
            columns[column_index].append(tab_index)
            self._column_heights[column_index] += (
                self._estimated_tab_height(tab) + _SETTING_ROW_GAP
            )

        assignments = tuple(tuple(column) for column in columns)
        heights = list(self._column_heights)
        return assignments, heights

    def _apply_column_plan(self, assignments: tuple[tuple[int, ...], ...]) -> None:
        self._clear_columns()

        for column_index, tab_indexes in enumerate(assignments):
            layout = self._layouts[column_index]
            for tab_index in tab_indexes:
                layout.addWidget(self._tabs[tab_index])
            layout.addStretch()

        self._column_assignments = assignments

    def _prepare_tabs_for_measurement(self) -> None:
        self.ensurePolished()
        self._scroll_area_content.ensurePolished()
        self._main_layout.activate()
        for tab in self._tabs:
            tab.ensurePolished()
            layout = tab.layout()
            if layout is not None:
                layout.activate()

    def _estimated_tab_height(self, tab: QWidget) -> int:
        if isinstance(tab, MTCollapsibleContainer):
            try:
                return 1 # TODO: fix # max(1, int(tab.effective_height_hint()))
            except Exception:
                pass

        fixed_height = tab.minimumHeight()
        if fixed_height > 0 and tab.maximumHeight() == fixed_height:
            return int(fixed_height)
        if tab.height() > 0:
            return int(tab.height())
        minimum_hint = (
            tab.minimumSizeHint().height() if tab.minimumSizeHint().isValid() else 0
        )
        layout = tab.layout()
        layout_hint = (
            layout.sizeHint().height() if layout is not None else 0
        )
        return max(1, int(max(tab.sizeHint().height(), minimum_hint, layout_hint)))

    def _clear_columns(self) -> None:
        for layout in self._layouts:
            while layout.count() > 0:
                item = layout.takeAt(0)
                if item is None:
                    continue

                widget = item.widget()
                if widget is not None:
                    widget.setParent(self._scroll_area_content)
