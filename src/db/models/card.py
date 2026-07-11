from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import CookieCheckerResult


class Card(BaseModel):
    __tablename__ = "cards"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    
    network: Mapped[str | None] = mapped_column(String(128))
    last_4_digits: Mapped[int | None] = mapped_column(Integer)
    expire_month: Mapped[int | None] = mapped_column(Integer)
    exprie_year: Mapped[int | None] = mapped_column(Integer)
    last_used: Mapped[int | None] = mapped_column(BigInteger)
    
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="card")
