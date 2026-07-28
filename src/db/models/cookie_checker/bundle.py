from __future__ import annotations

import typing as t

from sqlalchemy.orm import Mapped, relationship

from .base import CookieCheckerBase
from src.db.models.mixins import BaseMixin, BundleMixin, ResultBundleMixin


if t.TYPE_CHECKING:
    from . import CookieCheckerResult


class Bundle(CookieCheckerBase, BaseMixin, BundleMixin):
    __tablename__ = "bundles"


class BundleOwned(CookieCheckerBase, BaseMixin, ResultBundleMixin):
    __tablename__ = "bundles_owned"

    bundle: Mapped["Bundle"] = relationship()
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="bundles")
