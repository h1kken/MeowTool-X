from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import (
        Place,
        CookieCheckerResult,
    )


class Product(BaseModel):
    __tablename__ = "products"
    __table_args__ = UniqueConstraint("place_id", "name", name="uq_product_place_name")

    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), index=True)

    name: Mapped[str] = mapped_column(String(128))

    owned_records: Mapped[list["ProductOwned"]] = relationship(back_populates="product")

    place: Mapped["Place"] = relationship(back_populates="products")


class ProductOwned(BaseModel):
    __tablename__ = "products_owned"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    count: Mapped[int] = mapped_column(Integer)

    result: Mapped["CookieCheckerResult"] = relationship(back_populates="products")

    product: Mapped["Product"] = relationship(back_populates="owned_records")
