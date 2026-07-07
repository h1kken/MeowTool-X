from __future__ import annotations

from typing import Protocol, cast, runtime_checkable

from PySide6.QtCore import QEvent, QObject, Qt

from src.translation.manager import TranslationManager

_TRANSLATOR_REBIND_EVENTS: frozenset[QEvent.Type] = frozenset({
    QEvent.Type.ParentChange,
    QEvent.Type.Polish,
    QEvent.Type.Show,
})


class _TextWidget(Protocol):
    def setText(self, text: str) -> None: ...


class _ComboBoxWidget(Protocol):
    def addItem(self, text: str, user_data: object = ...) -> None: ...
    def count(self) -> int: ...
    def setItemData(self, index: int, value: object, role: int = ...) -> None: ...
    def itemData(self, index: int, role: int = ...) -> object | None: ...
    def setItemText(self, index: int, text: str) -> None: ...


@runtime_checkable
class _ComboBoxContentWidthWidget(_ComboBoxWidget, Protocol):
    def sync_content_width(self) -> None: ...


def _resolve_parent_translator(target: QObject) -> TranslationManager | None:
    current = target.parent()
    while current is not None:
        translator = getattr(current, '_translator', None)
        if isinstance(translator, TranslationManager):
            return translator
        current = current.parent()
    return None


class TranslationAwareMixin:
    def __init__(
        self,
        *args: object,
        translator: TranslationManager | None = None,
        **kwargs: object,
    ) -> None:
        self._translator: TranslationManager | None = None
        self._explicit_translator = translator
        super().__init__(*args, **kwargs)

    def event(self, event: QEvent) -> bool:
        if event.type() in _TRANSLATOR_REBIND_EVENTS:
            self._sync_translator_binding()
        return super().event(event)

    def translation_manager(self) -> TranslationManager | None:
        return self._translator

    def set_translation_manager(self, translator: TranslationManager | None) -> None:
        self._explicit_translator = translator
        self._sync_translator_binding(force=True)

    def _resolve_translation_manager(self) -> TranslationManager | None:
        if isinstance(self._explicit_translator, TranslationManager):
            return self._explicit_translator
        return _resolve_parent_translator(cast(QObject, self))

    def _sync_translator_binding(self, *, force: bool = False) -> None:
        next_translator = self._resolve_translation_manager()
        if not force and next_translator is self._translator:
            return

        previous = self._translator
        if previous is not None:
            try:
                previous.language_changed.disconnect(self._on_language_changed)
            except (RuntimeError, TypeError):
                pass

        self._translator = next_translator
        if next_translator is not None:
            next_translator.language_changed.connect(self._on_language_changed)

        self._on_translation_binding_changed(previous, next_translator)

    def _on_translation_binding_changed(
        self,
        _previous: TranslationManager | None,
        _current: TranslationManager | None,
    ) -> None:
        self._on_language_changed()

    def _on_language_changed(self) -> None:
        return


class TranslatableMixin(TranslationAwareMixin):
    def __init__(
        self,
        key: str,
        *args: object,
        translator: TranslationManager | None = None,
        **kwargs: object,
    ) -> None:
        self._key = key
        super().__init__(*args, translator=translator, **kwargs)

    def _on_language_changed(self) -> None:
        translator = self.translation_manager()
        cast(_TextWidget, self).setText(
            translator.tr(self._key) if translator is not None else self._key
        )
        

class TranslatableComboBoxMixin(TranslationAwareMixin):
    def __init__(
        self,
        *args: object,
        translator: TranslationManager | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, translator=translator, **kwargs)

    def add_item(self, item: str) -> None:
        combo = cast(_ComboBoxWidget, self)
        translator = self.translation_manager()
        combo.addItem(translator.tr(item) if translator is not None else item, item)
        index = combo.count() - 1
        combo.setItemData(index, item, Qt.ItemDataRole.UserRole + 1)

    def add_items(self, items: list[str]) -> None:
        for item in items:
            self.add_item(item)

    def _on_language_changed(self) -> None:
        combo = cast(_ComboBoxWidget, self)
        translator = self.translation_manager()
        for i in range(combo.count()):
            key = combo.itemData(i, Qt.ItemDataRole.UserRole + 1)
            if not isinstance(key, str):
                continue
            combo.setItemText(i, translator.tr(key) if translator is not None else key)
        if isinstance(self, _ComboBoxContentWidthWidget):
            self.sync_content_width()
