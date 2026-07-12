from .base import TransactionAnalysisBase
from src.db.models.mixins import BaseMixin, PlaceMixin


class Place(TransactionAnalysisBase, BaseMixin, PlaceMixin):
    __tablename__ = "places"
