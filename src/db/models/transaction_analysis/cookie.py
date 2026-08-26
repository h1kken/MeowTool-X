from __future__ import annotations

from src.db.mixins import BaseMixin, CookieMixin

from .base import TransactionAnalysisBase


class Cookie(TransactionAnalysisBase, BaseMixin, CookieMixin):
    __tablename__ = "cookies"
