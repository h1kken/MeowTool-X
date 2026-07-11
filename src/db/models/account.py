from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import (
        Cookie,
        CookieCheckerResult
    )


class Account(BaseModel):
    __tablename__ = "accounts"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(128))
    
    cookie_id: Mapped[int | None] = mapped_column(ForeignKey("cookies.id"), index=True)
    cookie: Mapped["Cookie | None"] = relationship(back_populates="accounts")
    
    results: Mapped[list["CookieCheckerResult"]] = relationship(back_populates="account")
