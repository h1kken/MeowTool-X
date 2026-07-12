from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column


class CookieMixin:
    cookie_ref_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cookie: Mapped[str] = mapped_column(Text, unique=True)
