from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Generic, TypeVar, cast

from sqlalchemy import delete as sql_delete
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy.orm import Session

TModel = TypeVar("TModel")
TResultModel = TypeVar("TResultModel")


class BaseRepository(Generic[TModel]):
    def __init__(self, session: Session, model_type: type[TModel]) -> None:
        self._session = session
        self._model_type = model_type

    @property
    def session(self) -> Session:
        return self._session

    @property
    def model_type(self) -> type[TModel]:
        return self._model_type

    def get_by_id(self, row_id: object) -> TModel | None:
        return self._session.get(self._model_type, row_id)

    def bulk_insert(self, rows: Iterable[Mapping[str, object]]) -> int:
        payload = [dict(row) for row in rows]
        if not payload:
            return 0

        self._session.execute(insert(self._model_type), payload)
        return len(payload)


class ResultRepository(BaseRepository[TResultModel], Generic[TResultModel]):
    def _query_model_type(self) -> Any:
        return cast(Any, self.model_type)

    def list_by_run(
        self,
        run_id: int,
        *,
        limit: int | None = None,
        after_id: int | None = None,
    ) -> list[TResultModel]:
        model_type = self._query_model_type()
        stmt = select(self.model_type).where(model_type.run_id == run_id)
        if after_id is not None:
            stmt = stmt.where(model_type.id > after_id)

        stmt = stmt.order_by(model_type.id.asc())
        if limit is not None:
            stmt = stmt.limit(limit)

        return list(self.session.scalars(stmt).all())

    def count_by_run(self, run_id: int) -> int:
        model_type = self._query_model_type()
        stmt = select(func.count()).select_from(self.model_type).where(
            model_type.run_id == run_id
        )
        return int(self.session.scalar(stmt) or 0)

    def delete_by_run(self, run_id: int) -> int:
        model_type = self._query_model_type()
        deleted_count = self.count_by_run(run_id)
        if deleted_count == 0:
            return 0

        stmt = sql_delete(self.model_type).where(model_type.run_id == run_id)
        self.session.execute(stmt)
        return deleted_count

    def bulk_insert_for_run(
        self,
        run_id: int,
        rows: Iterable[Mapping[str, object]],
    ) -> int:
        payload = [{**dict(row), "run_id": run_id} for row in rows]
        return self.bulk_insert(payload)

__all__ = ("BaseRepository", "ResultRepository")
