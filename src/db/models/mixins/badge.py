from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column


class BadgeMixin:    
    badge_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))


class ResultBadgeMixin:
    badge_ref_id: Mapped[int] = mapped_column(ForeignKey("badges.id"), index=True)
    result_ref_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
