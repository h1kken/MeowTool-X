from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.db.models import BaseModel
from src.db.mixins import BaseMixin


class CookieCheckerBase(DeclarativeBase, BaseModel):
    pass


class CookieCheckerResultBase(CookieCheckerBase, BaseMixin):
    __abstract__ = True

    run_ref_id: Mapped[int] = mapped_column(ForeignKey('runs.id'), index=True)
