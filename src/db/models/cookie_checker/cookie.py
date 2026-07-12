from __future__ import annotations

from .base import CookieCheckerBase
from src.db.models.mixins import BaseMixin, CookieMixin


class Cookie(CookieCheckerBase, BaseMixin, CookieMixin):
    __tablename__ = "cookies"
