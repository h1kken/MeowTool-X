from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import CookieCheckerResult


class Session(BaseModel):
    __tablename__ = "sessions"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    
    city: Mapped[str | None] = mapped_column(String(128))
    subdivision: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(128))
    last_ip: Mapped[str | None] = mapped_column(String(128))
    is_trusted: Mapped[bool | None] = mapped_column(Boolean)
    
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="sessions")
