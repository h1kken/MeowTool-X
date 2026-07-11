from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import Account


class Cookie(BaseModel):
    __tablename__ = "cookies"

    cookie_id: Mapped[str] = mapped_column(Integer, primary_key=True)
    cookie: Mapped[str] = mapped_column(Text, unique=True)

    accounts: Mapped[list["Account"]] = relationship(back_populates="cookie")
