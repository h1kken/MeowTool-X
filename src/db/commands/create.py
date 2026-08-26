import typing as t

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from .base import ExecutableDatabaseCommand


@dataclass(slots=True)
class CreateModelCommand(ExecutableDatabaseCommand):
    model: type[t.Any]
    values: dict[str, t.Any] = field(default_factory=lambda: {})
    callback: t.Callable[[t.Any], None] | None = None

    def execute(self, session: Session) -> None:
        obj = self.model(**self.values)

        session.add(obj)
        session.commit()

        if self.callback is not None:
            self.callback(obj)
