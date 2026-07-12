from time import monotonic
from queue import Queue, Empty
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.db.manager import DatabaseHandler
    from src.db.models.cookie_checker import CookieCheckerResult


class DatabaseWriter:
    def __init__(self, handler: DatabaseHandler):
        self.queue: Queue[CookieCheckerResult] = Queue(maxsize=500)
        self.handler = handler
        self.running = True

    def put(self, obj: CookieCheckerResult):
        self.queue.put(obj)

    def run(self):
        session = self.handler.session()

        batch: list[CookieCheckerResult] = []
        last_commit = monotonic()

        while self.running:
            try:
                obj = self.queue.get(timeout=1)
                batch.append(obj)
            except Empty:
                pass

            if len(batch) >= 100 or (batch and monotonic() - last_commit >= 5):
                session.add_all(batch)
                session.commit()
                session.expunge_all()

                batch.clear()
                last_commit = monotonic()
