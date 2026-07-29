from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column


class PlaceMixin:
    place_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(128))


class ResultPlaceMixin:
    place_ref_id: Mapped[int] = mapped_column(ForeignKey('places.id'), index=True)
    result_ref_id: Mapped[int] = mapped_column(ForeignKey('results.id'), index=True)
