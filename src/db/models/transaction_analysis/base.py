from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.db.models.mixins import BaseMixin, RunMixin


class TransactionAnalysisBase(DeclarativeBase):
    pass


class TransactionAnalysisRun(TransactionAnalysisBase, BaseMixin, RunMixin):
    __tablename__ = "runs"


class TransactionAnalysisResultBase(TransactionAnalysisBase, BaseMixin):
    __abstract__ = True

    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
