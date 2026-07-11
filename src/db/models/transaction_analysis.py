from __future__ import annotations

from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models import RunModel, ResultModel


class TransactionAnalysisRun(RunModel):
    __tablename__ = "runs"


class TransactionAnalysisResult(ResultModel):
    __tablename__ = "results"

    is_valid: Mapped[bool | None] = mapped_column(Boolean, index=True)
    
    places:
    
    cookie: Mapped[str] = mapped_column(Text)


__all__ = (
    "TransactionAnalysisRun",
    "TransactionAnalysisResult",
)