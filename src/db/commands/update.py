import typing as t

from dataclasses import dataclass

from sqlalchemy import update
from sqlalchemy.orm import Session

from .base import ExecutableDatabaseCommand


@dataclass(slots=True)
class UpdateModelCommand(ExecutableDatabaseCommand):
    model: type[t.Any]
    id: int
    values: dict[str, t.Any]

    def execute(self, session: Session) -> None:
        session.execute(
            update(self.model)
            .where(self.model.id == self.id)
            .values(**self.values),
        )
        session.commit()