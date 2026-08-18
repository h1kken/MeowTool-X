from __future__ import annotations

import typing as t

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import TransactionAnalysisResultBase

if t.TYPE_CHECKING:
    from . import Cookie, Transaction


class TransactionAnalysisResult(TransactionAnalysisResultBase):
    __tablename__ = 'results'

    is_valid: Mapped[bool | None] = mapped_column(Boolean, index=True)

    cookie_id: Mapped[int] = mapped_column(ForeignKey('cookies.id'))
    cookie: Mapped['Cookie'] = relationship(back_populates='cookie')

    transactions: Mapped[list['Transaction']] = relationship(back_populates='result')
