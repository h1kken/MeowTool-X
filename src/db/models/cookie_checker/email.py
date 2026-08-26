from __future__ import annotations

import typing as t

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.mixins import BaseMixin, EmailMixin

from .base import CookieCheckerBase

if t.TYPE_CHECKING:
    from . import CookieCheckerResult


class Email(CookieCheckerBase, BaseMixin, EmailMixin):
    __tablename__ = 'emails'
    
    result_ref_id: Mapped[int] = mapped_column(ForeignKey('results.id'), unique=True, index=True)
    result: Mapped['CookieCheckerResult'] = relationship(back_populates='email')
