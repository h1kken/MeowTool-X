from __future__ import annotations

import typing as t

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.mixins import BaseMixin, AccountMixin

from .base import CookieCheckerBase

if t.TYPE_CHECKING:
    from . import Cookie, CookieCheckerResult


class Account(CookieCheckerBase, BaseMixin, AccountMixin):
    __tablename__ = 'accounts'

    cookie_ref_id: Mapped[int | None] = mapped_column(ForeignKey('cookies.id'), index=True)
    cookie: Mapped['Cookie | None'] = relationship(back_populates='accounts')

    results: Mapped[list['CookieCheckerResult']] = relationship(back_populates='account')
