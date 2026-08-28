import typing as t

from time import monotonic
from queue import Queue, Empty

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from sqlalchemy.engine import CursorResult

from PySide6.QtCore import QObject, Signal

from src.utils.logging import logger

from .manager import DatabaseHandler
from .commands import DatabaseCommand, BatchableDatabaseCommand, ExecutableDatabaseCommand, StopDatabaseWriterCommand

T = t.TypeVar('T')


class DatabaseWriter(QObject):
    batchWritten = Signal(int, dict)
    
    BATCH_SIZE = 1000
    COMMIT_INTERVAL = 5
    
    def __init__(
        self,
        handler: DatabaseHandler,
        model: type[T],
        callback: t.Callable[[dict[str, int]], None] | None = None,
    ) -> None:
        self._handler = handler
        self._model = model
        self._callback = callback
        
        self._queue: Queue[DatabaseCommand] = Queue(maxsize=10_000)
        
    def put(self, command: DatabaseCommand) -> None:
        self._queue.put(command)

    def run(self) -> None:
        session = self._handler.session()

        batches: dict[int, list[BatchableDatabaseCommand]] = {}
        last_batch_write = monotonic()

        def process_batch(session: Session, run_id: int, batch: list[BatchableDatabaseCommand]):
            if not batch:
                return
            
            nonlocal last_batch_write
            self._write_batch(session, run_id, batch)
            batch.clear()
            last_batch_write = monotonic()

        try:
            while True:
                try:
                    command = self._queue.get(timeout=1)
                except Empty:
                    command = None
                
                if (monotonic() - last_batch_write) >= self.COMMIT_INTERVAL:
                    for run_id, batch in batches.items():
                        process_batch(session, run_id, batch)

                if command is None:
                    continue
                
                match command:
                    
                    case BatchableDatabaseCommand():
                        batch = batches.setdefault(command.run_id, [])
                        batch.append(command)
                        
                        if len(batch) >= self.BATCH_SIZE:
                            process_batch(session, command.run_id, batch)
                    
                    case ExecutableDatabaseCommand():
                        batch = batches[command.run_id]
                        process_batch(session, command.run_id, batch)

                        command.execute(session)
                        session.commit()
                    
                    case StopDatabaseWriterCommand():
                        break
                    
                    case _:
                        logger.warning(f'Unknown database command: {command!r}')

            for run_id, batch in batches.items():
                process_batch(session, run_id, batch)
         
        except Exception as e: # TODO: if writer dies - all runs dies too
            session.rollback()
            logger.error(f'Failed to write batch: model={self._model.__name__}, error={type(e).__name__}: {getattr(e, 'orig', e)}')
            
        finally:
            session.close()
    
    def stop(self) -> None:
        self._queue.put(StopDatabaseWriterCommand())
    
    def _write_batch(self, session: Session, run_id: int, batch: list[BatchableDatabaseCommand]) -> None:
        rows = [command.values for command in batch]
        
        stmt = insert(self._model).values(rows).on_conflict_do_nothing()
        result = t.cast(CursorResult[t.Any], session.execute(stmt))

        inserted = result.rowcount
        duplicates = len(batch) - inserted

        session.commit()

        self.batchWritten.emit(
            run_id,
            {
                'inserted': inserted,
                'duplicate': duplicates,
            }
        )
