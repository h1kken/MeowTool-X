from __future__ import annotations

import typing as t

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import CookieCheckerBase
from src.db.models.mixins import BaseMixin, GroupMixin, ResultGroupMixin

if t.TYPE_CHECKING:
    from . import CookieCheckerResult


class Group(CookieCheckerBase, BaseMixin, GroupMixin):
    __tablename__ = 'groups'


class GroupExtended(CookieCheckerBase, BaseMixin):
    __tablename__ = 'groups_extended'
    
    group_ref_id: Mapped[int] = mapped_column(ForeignKey('groups.id'), unique=True)
    group: Mapped['Group'] = relationship(back_populates='extended')
    
    robux_pending: Mapped[int | None] = mapped_column(BigInteger)
    robux_funds: Mapped[int | None] = mapped_column(BigInteger)


class GroupOwned(CookieCheckerBase, BaseMixin, ResultGroupMixin):
    __tablename__ = 'groups_owned'

    group: Mapped['Group'] = relationship()
    result: Mapped['CookieCheckerResult'] = relationship(back_populates='groups_owned')
