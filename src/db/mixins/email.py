from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column


class EmailMixin:
    email: Mapped[str] = mapped_column(String(128))
    setted: Mapped[bool] = mapped_column(Boolean)
    verified: Mapped[bool] = mapped_column(Boolean)
