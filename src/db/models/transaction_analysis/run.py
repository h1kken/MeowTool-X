from src.db.mixins import BaseMixin, RunMixin

from .base import TransactionAnalysisBase


class TransactionAnalysisRun(TransactionAnalysisBase, BaseMixin, RunMixin):
    __tablename__ = 'runs'
