from __future__ import annotations

from .base import TransactionAnalysisBase
from src.db.models.mixins import BaseMixin, CookieMixin


class Cookie(TransactionAnalysisBase, BaseMixin, CookieMixin):
    __tablename__ = "cookies"
