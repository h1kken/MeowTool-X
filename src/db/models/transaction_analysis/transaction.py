from __future__ import annotations

import typing as t

from sqlalchemy.orm import Mapped, relationship

from src.db.mixins import BaseMixin, TransactionMixin, ResultPlaceMixin

from .base import TransactionAnalysisBase

if t.TYPE_CHECKING:
    from . import TransactionAnalysisResult, Place


class Transaction(TransactionAnalysisBase, BaseMixin, TransactionMixin, ResultPlaceMixin):
    __tablename__ = 'transactions'

    place: Mapped['Place'] = relationship(back_populates='extended')
    result: Mapped['TransactionAnalysisResult'] = relationship(back_populates='transactions')
