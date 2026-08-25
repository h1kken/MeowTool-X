from sqlalchemy.orm import Session


class DatabaseCommand:
    pass


class BatchableDatabaseCommand(DatabaseCommand):
    pass


class ExecutableDatabaseCommand(DatabaseCommand):
    def execute(self, session: Session) -> None:
        raise NotImplementedError
