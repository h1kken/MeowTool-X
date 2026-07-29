from __future__ import annotations

import typing as t

from sqlalchemy.orm import Mapped, relationship

from .base import TransactionAnalysisBase
from src.db.models.mixins import BaseMixin, TransactionMixin, ResultPlaceMixin

if t.TYPE_CHECKING:
    from . import TransactionAnalysisResult, Place


class Transaction(TransactionAnalysisBase, BaseMixin, TransactionMixin, ResultPlaceMixin):
    __tablename__ = 'transactions'

    place: Mapped['Place'] = relationship(back_populates='extended')
    result: Mapped['TransactionAnalysisResult'] = relationship(back_populates='transactions')
