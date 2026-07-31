from src.ui.pages import BasePage


type PageSpec = tuple[str | None, str, str, type[BasePage]]


__all__ = (
    'PageSpec',
)
