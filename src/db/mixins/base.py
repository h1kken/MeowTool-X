from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


class BaseMixin:
    id: Mapped[int] = mapped_column(primary_key=True)


class RunMixin:
    started_at: Mapped[datetime] = mapped_column(DateTime())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime())
    status: Mapped[str] = mapped_column(String(32))
