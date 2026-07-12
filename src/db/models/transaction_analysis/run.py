from .base import TransactionAnalysisBase
from src.db.models.mixins import BaseMixin, RunMixin


class TransactionAnalysisRun(TransactionAnalysisBase, BaseMixin, RunMixin):
    __tablename__ = "runs"
