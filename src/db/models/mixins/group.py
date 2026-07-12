from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class GroupMixin:
    group_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(128))
    members_count: Mapped[int | None] = mapped_column(Integer)


class ResultGroupMixin:
    group_ref_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    result_ref_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
