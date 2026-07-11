from datetime import datetime

from sqlalchemy import ForeignKey, Integer, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    
class RunModel(BaseModel):
    __abstract__ = True

    started_at: Mapped[datetime] = mapped_column(DateTime())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime())
    status: Mapped[str] = mapped_column(String(32))


class ResultModel(BaseModel):
    __abstract__ = True

    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
