from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import (
        Place,
        TransactionAnalysisResult,
    )


class Transaction(BaseModel):
    __tablename__ = "transactions"

    type: Mapped[str] = mapped_column(String(32))
    name: Mapped[str | None] = mapped_column(String(128))
    price: Mapped[int | None] = mapped_column(BigInteger)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime)

    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), unique=True)
    place: Mapped["Place"] = relationship(back_populates="extended")

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    result: Mapped["TransactionAnalysisResult"] = relationship(back_populates="transactions")
