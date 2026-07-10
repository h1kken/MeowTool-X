from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    
    
class RunModel(BaseModel):
    __abstract__ = True

    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]
    status: Mapped[str]


class ResultModel(BaseModel):
    __abstract__ = True

    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
