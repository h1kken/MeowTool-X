from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import CookieCheckerResult


class Email(BaseModel):
    __tablename__ = "emails"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), unique=True, index=True)
    
    email: Mapped[str] = mapped_column(String(128))
    setted: Mapped[bool] = mapped_column(Boolean)
    verified: Mapped[bool] = mapped_column(Boolean)
    
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="email")
