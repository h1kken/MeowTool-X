from sqlalchemy.orm import Session

from .run import CookieSorterRun


class CookieSorterRepository:
    def __init__(self, session: Session):
        self._session = session

    def create_run(self) -> CookieSorterRun:
        run = CookieSorterRun()
        self._session.add(run)
        self._session.flush()
        return run