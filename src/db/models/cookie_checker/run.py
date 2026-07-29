from .base import CookieCheckerBase
from src.db.models.mixins import BaseMixin, RunMixin


class CookieCheckerRun(CookieCheckerBase, BaseMixin, RunMixin):
    __tablename__ = 'runs'
