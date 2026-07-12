from .base import CookieRefresherBase
from src.db.models.mixins import BaseMixin, RunMixin


class CookieRefresherRun(CookieRefresherBase, BaseMixin, RunMixin):
    __tablename__ = "runs"
