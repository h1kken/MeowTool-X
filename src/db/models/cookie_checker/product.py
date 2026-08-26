from __future__ import annotations

import typing as t

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.mixins import BaseMixin, ProductMixin, ResultProductMixin

from .base import CookieCheckerBase

if t.TYPE_CHECKING:
    from . import CookieCheckerResult, Place


class Product(CookieCheckerBase, BaseMixin, ProductMixin):
    __tablename__ = 'products'
    __table_args__ = (
        UniqueConstraint('product_id', 'name', name='uq_product_name'),
    )
    
    place_ref_id: Mapped[int] = mapped_column(ForeignKey('places.id'), index=True)
    place: Mapped['Place'] = relationship(back_populates='products')


class ProductOwned(CookieCheckerBase, BaseMixin, ResultProductMixin):
    __tablename__ = 'products_owned'

    product: Mapped['Product'] = relationship()
    result: Mapped['CookieCheckerResult'] = relationship(back_populates='products')

    count: Mapped[int] = mapped_column(Integer)
