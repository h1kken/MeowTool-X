from src.db.mixins import BaseMixin, RunMixin

from .base import CookieRefresherBase


class CookieRefresherRun(CookieRefresherBase, BaseMixin, RunMixin):
    __tablename__ = 'runs'
