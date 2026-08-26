from src.db.mixins import BaseMixin, RunMixin

from .base import CookieSorterBase


class CookieSorterRun(CookieSorterBase, BaseMixin, RunMixin):
    __tablename__ = 'runs'
