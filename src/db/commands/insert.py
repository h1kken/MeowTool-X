from dataclasses import dataclass

from src.db.commands.base import BatchableDatabaseCommand


@dataclass(slots=True)
class InsertCommand(BatchableDatabaseCommand):
    pass
