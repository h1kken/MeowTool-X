from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


class TransactionMixin:
    type: Mapped[str] = mapped_column(String(32))
    name: Mapped[str | None] = mapped_column(String(128))
    price: Mapped[int | None] = mapped_column(BigInteger)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime)
