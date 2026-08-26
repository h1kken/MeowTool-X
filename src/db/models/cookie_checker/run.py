from src.db.mixins import BaseMixin, RunMixin

from .base import CookieCheckerBase


class CookieCheckerRun(CookieCheckerBase, BaseMixin, RunMixin):
    __tablename__ = 'runs'
