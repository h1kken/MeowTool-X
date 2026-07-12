from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.db.models.mixins import BaseMixin, RunMixin


class CookieCheckerBase(DeclarativeBase):
    pass


class CookieCheckerRun(CookieCheckerBase, BaseMixin, RunMixin):
    __tablename__ = "runs"


class CookieCheckerResultBase(CookieCheckerBase, BaseMixin):
    __abstract__ = True

    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
