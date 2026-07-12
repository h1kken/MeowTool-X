from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column


class SessionMixin:
    city: Mapped[str | None] = mapped_column(String(128))
    subdivision: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(128))
    last_ip: Mapped[str | None] = mapped_column(String(128))
    is_trusted: Mapped[bool | None] = mapped_column(Boolean)
