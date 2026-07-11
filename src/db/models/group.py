from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import CookieCheckerResult


class Group(BaseModel):
    __tablename__ = "groups"

    group_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(128))
    owner_id: Mapped[int] = mapped_column(ForeignKey("results.user_id"), index=True)
    members_count: Mapped[int | None] = mapped_column(Integer)
    robux_pending: Mapped[int | None] = mapped_column(BigInteger)
    robux_funds: Mapped[int | None] = mapped_column(BigInteger)

    owned_records: Mapped[list["GroupOwned"]] = relationship(back_populates="group")


class GroupOwned(BaseModel):
    __tablename__ = "groups_owned"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.group_id"), index=True)

    result: Mapped["CookieCheckerResult"] = relationship(back_populates="groups_owned")
    
    group: Mapped["Group"] = relationship(back_populates="owned_records")