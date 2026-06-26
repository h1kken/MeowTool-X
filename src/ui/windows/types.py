from PySide6.QtWidgets import QWidget

type PageSpec = tuple[str, str, type[QWidget]]
type SidebarSectionSpec = tuple[
    str, str, list[PageSpec] | type[QWidget] | None
]

__all__ = ("PageSpec", "SidebarSectionSpec")
