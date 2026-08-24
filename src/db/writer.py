from time import monotonic
from queue import Queue, Empty
import typing as t

from sqlalchemy import inspect
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Mapper, Session
from sqlalchemy.engine import CursorResult

from .manager import DatabaseHandler

T = t.TypeVar('T')


class DatabaseWriter(t.Generic[T]):
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
        
        self._queue: Queue[T] = Queue()
        self._running = False
        self._duplicates = 0

    def put(self, obj: T) -> None:
        self._queue.put(obj)

    def run(self) -> None:
        session = self._handler.session()

        batch: list[T] = []
        last_commit = monotonic()

        self._running = True
        while self._running:
            try:
                obj = self._queue.get(timeout=1)
                batch.append(obj)
            except Empty:
                pass

            if len(batch) >= self.BATCH_SIZE or (batch and monotonic() - last_commit >= self.COMMIT_INTERVAL):
                self._write_batch(session, batch)

                batch.clear()
                last_commit = monotonic()
                
        if batch:
            session.add_all(batch)
            session.commit()
            
        session.close()
    
    def stop(self) -> None:
        self._running = False
    
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
