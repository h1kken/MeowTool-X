from time import monotonic
from queue import Queue, Empty
import typing as t

if t.TYPE_CHECKING:
    from src.db.manager import DatabaseHandler
    from src.db.models.cookie_checker import CookieCheckerResult


# TODO: move to advanced config
_BATCH_SIZE = 100
_COMMIT_INTERVAL = 5


class DatabaseWriter:
    def __init__(self, handler: DatabaseHandler):
        self._handler = handler
        
        self._queue: Queue[CookieCheckerResult] = Queue()
        self._running = False

    def put(self, obj: CookieCheckerResult) -> None:
        self._queue.put(obj)

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        session = self._handler.session()

        batch: list[CookieCheckerResult] = []
        last_commit = monotonic()

        self._running = True
        while self._running:
            try:
                obj = self._queue.get(timeout=1)
                batch.append(obj)
            except Empty:
                pass

            if len(batch) >= _BATCH_SIZE or (batch and monotonic() - last_commit >= _COMMIT_INTERVAL):
                session.add_all(batch)
                session.commit()
                session.expunge_all()

                batch.clear()
                last_commit = monotonic()
                
        if batch:
            session.add_all(batch)
            session.commit()
            
        session.close()
