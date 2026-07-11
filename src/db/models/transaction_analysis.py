from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import RunModel, ResultModel

if TYPE_CHECKING:
    from src.db.models import (
        Cookie,
        Transaction,
    )


class TransactionAnalysisRun(RunModel):
    __tablename__ = "runs"


class TransactionAnalysisResult(ResultModel):
    __tablename__ = "results"

    is_valid: Mapped[bool | None] = mapped_column(Boolean, index=True)

    cookie_id: Mapped[int] = mapped_column(ForeignKey("cookies.id"))
    cookie: Mapped["Cookie"] = relationship(back_populates="cookie")

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="result")


__all__ = (
    "TransactionAnalysisRun",
    "TransactionAnalysisResult",
)