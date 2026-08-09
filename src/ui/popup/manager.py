from src.ui.widgets.common import MTPopupOverlay, MTWidget


class PopupManager:
    def __init__(
        self,
        overlay: MTPopupOverlay,
    ) -> None:
        self._overlay = overlay
        self._current_popup: MTWidget | None = None

    @property
    def is_open(self) -> bool:
        return self._current_popup is not None

    def show(self, popup: MTWidget) -> None:
        self.close()

        self._current_popup = popup
        self._overlay.showPopup(popup)

    def close(self) -> None:
        if self._current_popup is None:
            return

        self._overlay.closePopup()
        self._current_popup = None

    def toggle(self, popup: MTWidget) -> None:
        if self.is_open:
            self.close()
        else:
            self.show(popup)
