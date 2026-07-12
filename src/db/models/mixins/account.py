from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column


class AccountMixin:
    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(128))
