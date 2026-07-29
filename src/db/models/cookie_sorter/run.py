from .base import CookieSorterBase
from src.db.models.mixins import BaseMixin, RunMixin


class CookieSorterRun(CookieSorterBase, BaseMixin, RunMixin):
    __tablename__ = 'runs'
