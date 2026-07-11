from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import CookieCheckerResult


class Bundle(BaseModel):
    __tablename__ = "bundles"

    bundle_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))

    owned_records: Mapped[list["BundleOwned"]] = relationship(back_populates="owned_records")


class BundleOwned(BaseModel):
    __tablename__ = "bundles_owned"

    bundle_id: Mapped[int] = mapped_column(ForeignKey("bundles.bundle_id"), index=True)
    bundle: Mapped["Bundle"] = relationship(back_populates="owned_records")

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="bundles")
