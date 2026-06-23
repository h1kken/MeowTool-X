from __future__ import annotations

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import RunBoundModel
from src.db.types import JsonValue


# TODO: columns
class CookieSorterResult(RunBoundModel):
    __tablename__ = "cookie_sorter_results"

    source_text: Mapped[str] = mapped_column(Text)
    extracted_cookie: Mapped[str | None] = mapped_column(Text)
    warning_text: Mapped[str | None] = mapped_column(Text)
    is_valid_cookie: Mapped[bool | None] = mapped_column(Boolean)
    bucket_name: Mapped[str | None] = mapped_column(String(64), index=True)
    output_path: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[JsonValue | None] = mapped_column(JSON)


__all__ = ("CookieSorterResult",)
