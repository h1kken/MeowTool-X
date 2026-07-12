from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session


@dataclass(slots=True)
class DatabaseFacade:
    session: Session

    def __getattr__(self, name: str) -> Any:
        return getattr(self.session, name)

    def __dir__(self) -> list[str]:
        return sorted(set(object.__dir__(self)) | set(dir(self.session)))


def build_facade(session: Session) -> DatabaseFacade:
    return DatabaseFacade(session=session)


__all__ = ("DatabaseFacade", "build_facade")
