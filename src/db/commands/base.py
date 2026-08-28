from dataclasses import dataclass

from sqlalchemy.orm import Session


class DatabaseCommand:
    pass


@dataclass(slots=True)
class BatchableDatabaseCommand(DatabaseCommand):
    run_id: int
    values: dict[str, object]


@dataclass(slots=True)
class ExecutableDatabaseCommand(DatabaseCommand):
    run_id: int
    
    def execute(self, session: Session) -> None:
        raise NotImplementedError
