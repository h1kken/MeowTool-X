from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.db.mixins import BaseMixin, RunMixin

from .base import CookieSorterBase


class CookieSorterRun(CookieSorterBase, BaseMixin, RunMixin):
    __tablename__ = 'runs'

    valid_count: Mapped[int] = mapped_column(default=0)
    duplicate_count: Mapped[int] = mapped_column(default=0)
    invalid_count: Mapped[int] = mapped_column(default=0)

    data: Mapped[list[str]] = mapped_column(JSON)
