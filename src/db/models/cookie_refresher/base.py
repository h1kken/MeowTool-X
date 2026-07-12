from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.db.models.mixins import BaseMixin, RunMixin


class CookieRefresherBase(DeclarativeBase):
    pass


class CookieRefresherRun(CookieRefresherBase, BaseMixin, RunMixin):
    __tablename__ = "runs"


class CookieRefresherResultBase(CookieRefresherBase, BaseMixin):
    __abstract__ = True

    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
