from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Generic, TypeVar

from sqlalchemy import Select
from sqlalchemy import delete as sql_delete
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.base import Base, RunBoundModel

TModel = TypeVar("TModel", bound=Base)
TRunBoundModel = TypeVar("TRunBoundModel", bound=RunBoundModel)


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

    def create(self, **values: object) -> TModel:
        instance = self._model_type(**values)
        return self.add(instance)

    def add(self, instance: TModel) -> TModel:
        self._session.add(instance)
        self._session.flush()
        return instance

    def create_many(self, rows: Sequence[Mapping[str, object]]) -> list[TModel]:
        instances = [
            self._model_type(**dict(row))
            for row in rows
        ]
        return self.add_many(instances)

    def add_many(self, instances: Iterable[TModel]) -> list[TModel]:
        rows = list(instances)
        if not rows:
            return rows
        self._session.add_all(rows)
        self._session.flush()
        return rows

    def bulk_insert(self, rows: Sequence[Mapping[str, object]]) -> int:
        if not rows:
            return 0
        payload = [dict(row) for row in rows]
        self._session.execute(insert(self._model_type), payload)
        self._session.flush()
        return len(payload)

    def delete_by_id(self, row_id: object) -> bool:
        instance = self.get_by_id(row_id)
        if instance is None:
            return False
        self.remove_instance(instance)
        return True

    def remove_instance(self, instance: TModel) -> None:
        self._session.delete(instance)
        self._session.flush()


class RunBoundRepository(BaseRepository[TRunBoundModel], Generic[TRunBoundModel]):
    def _select_by_run(self, run_id: int) -> Select[tuple[TRunBoundModel]]:
        return select(self.model_type).where(self.model_type.run_id == run_id)

    def list_by_run(
        self,
        run_id: int,
        *,
        limit: int | None = None,
        after_id: int | None = None,
    ) -> list[TRunBoundModel]:
        stmt = self._select_by_run(run_id)
        if after_id is not None:
            stmt = stmt.where(self.model_type.id > after_id)
        stmt = stmt.order_by(self.model_type.id.asc())
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).all())

    def count_by_run(self, run_id: int) -> int:
        stmt = select(func.count()).select_from(self.model_type).where(
            self.model_type.run_id == run_id
        )
        return int(self.session.scalar(stmt) or 0)

    def delete_by_run(self, run_id: int) -> int:
        deleted_count = self.count_by_run(run_id)
        if deleted_count == 0:
            return 0
        stmt = sql_delete(self.model_type).where(self.model_type.run_id == run_id)
        self.session.execute(stmt)
        self.session.flush()
        return deleted_count

    def bulk_insert_for_run(
        self,
        run_id: int,
        rows: Sequence[Mapping[str, object]],
    ) -> int:
        payload = [{**dict(row), "run_id": run_id} for row in rows]
        return self.bulk_insert(payload)

    def replace_for_run(
        self,
        run_id: int,
        rows: Sequence[Mapping[str, object]],
    ) -> int:
        self.delete_by_run(run_id)
        return self.bulk_insert_for_run(run_id, rows)


__all__ = ("BaseRepository", "RunBoundRepository")
