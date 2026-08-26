import typing as t

import threading
from time import monotonic
from queue import Queue, Empty

from sqlalchemy import inspect
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Mapper, Session
from sqlalchemy.engine import CursorResult

from .manager import DatabaseHandler
from .commands import BatchableDatabaseCommand

T = t.TypeVar('T')


class DatabaseCommand(t.Protocol):
    def execute(self, session: Session) -> None: ...


class DatabaseWriter:
    BATCH_SIZE = 100
    COMMIT_INTERVAL = 5
    
    def __init__(
        self,
        handler: DatabaseHandler,
        model: type[T],
        on_duplicates: t.Callable[[int], None] | None = None,
    ) -> None:
        self._handler = handler
        self._model = model
        self._on_duplicates = on_duplicates
        
        self._queue: Queue[DatabaseCommand] = Queue()
        self._duplicates = 0
        
        self._stop_event = threading.Event()

    def put(self, command: DatabaseCommand) -> None:
        self._queue.put(command)

    def run(self) -> None:
        session = self._handler.session()

        batch: list[BatchableDatabaseCommand] = []
        last_commit = monotonic()

        try:
            while not self._stop_event.is_set():
                try:
                    command = self._queue.get(timeout=1)
                except Empty:
                    if batch and (monotonic() - last_commit) >= self.COMMIT_INTERVAL:
                        self._write_batch(session, batch)
                        batch.clear()
                        last_commit = monotonic()
                        
                    continue

                # add record to batch
                if isinstance(command, BatchableDatabaseCommand):
                    batch.append(command)

                # check if other command
                else:
                    if batch:
                        self._write_batch(session, batch)
                        batch.clear()
                        last_commit = monotonic()

                    command.execute(session)
                    session.commit()
                    continue

            if batch:
                self._write_batch(session, batch)
                
        finally:
            session.close()
    
    def stop(self) -> None:
        self._stop_event.set()
    
    def _write_batch(
        self,
        session: Session,
        batch: list[T],
    ) -> None:
        mapper = t.cast(Mapper[t.Any], inspect(self._model))

        rows = [
            {
                column.key: getattr(obj, column.key)
                for column in mapper.columns
                if column.key in mapper.column_attrs
            }
            for obj in batch
        ]
        stmt = insert(self._model).values(rows).on_conflict_do_nothing()
        result = t.cast(CursorResult[t.Any], session.execute(stmt))

        inserted = result.rowcount
        duplicates = len(batch) - inserted

        session.commit()

        self._duplicates += duplicates

        if self._on_duplicates is not None:
            self._on_duplicates(self._duplicates)
