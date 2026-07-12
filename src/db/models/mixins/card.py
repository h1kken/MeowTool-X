from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class CardMixin:
    network: Mapped[str | None] = mapped_column(String(128))
    last_4_digits: Mapped[int | None] = mapped_column(Integer)
    expire_month: Mapped[int | None] = mapped_column(Integer)
    exprie_year: Mapped[int | None] = mapped_column(Integer)
    last_used: Mapped[int | None] = mapped_column(BigInteger)
