from __future__ import annotations

import hashlib

from sqlalchemy import ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from .base import CookieSorterResultBase


class CookieSorterResult(CookieSorterResultBase):
    __tablename__ = 'results'
    __table_args__ = (
        UniqueConstraint('run_ref_id', 'cookie_hash', name='uq_run_cookie_hash'),
    )

    run_ref_id: Mapped[int] = mapped_column(ForeignKey('runs.id'), index=True, nullable=False)

    cookie: Mapped[str] = mapped_column(String, nullable=False)
    cookie_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)

    @validates('cookie')
    def _set_cookie_hash(self, _key: str, value: str) -> str:
        self.cookie_hash = hashlib.sha256(value.encode()).digest()
        return value
