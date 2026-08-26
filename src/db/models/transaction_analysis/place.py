from src.db.mixins import BaseMixin, PlaceMixin

from .base import TransactionAnalysisBase


class Place(TransactionAnalysisBase, BaseMixin, PlaceMixin):
    __tablename__ = "places"
