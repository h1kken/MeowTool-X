from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AccountUpsertInput(BaseModel):
    lookup: dict[str, Any]
    values: dict[str, Any] = Field(default_factory=dict)
    cookies: set[str] = Field(default_factory=set)


class AccountBatchUpsertInput(BaseModel):
    items: list[AccountUpsertInput] = Field(default_factory=list)
    batch_size: int = 250


class AccountQueryInput(BaseModel):
    filters: dict[str, Any] = Field(default_factory=dict)
    fields: list[str] | None = None
    limit: int = 100
    offset: int = 0
    order_by: str | None = None
    descending: bool = False
    include_cookies: bool = True


class CookieAppendInput(BaseModel):
    lookup: dict[str, Any]
    cookies: set[str] = Field(default_factory=set)

