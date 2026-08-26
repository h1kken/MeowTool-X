from __future__ import annotations

from src.db.mixins import BaseMixin, CookieMixin

from .base import CookieCheckerBase


class Cookie(CookieCheckerBase, BaseMixin, CookieMixin):
    __tablename__ = 'cookies'
