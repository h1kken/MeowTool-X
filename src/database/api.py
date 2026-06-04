from __future__ import annotations

from typing import Any, Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.manager import Database
from src.database.models.roblox.cookie_checker.account import Account, BaseCookieChecker
from src.database.schemas import (
    AccountBatchUpsertInput,
    AccountQueryInput,
    AccountUpsertInput,
    CookieAppendInput,
)


def _validate_model(model_cls, payload):
    if isinstance(payload, model_cls):
        return payload
    if hasattr(model_cls, 'model_validate'):
        return model_cls.model_validate(payload)
    return model_cls.parse_obj(payload)


class DatabaseFunctionAPI:
    _LOOKUP_FIELDS = {'id', 'p_id', 'p_name', 'p_display_name'}
    _ALL_ACCOUNT_FIELDS = {column.name for column in Account.__table__.columns}
    _MUTABLE_ACCOUNT_FIELDS = _ALL_ACCOUNT_FIELDS - {'id'}
    _MAX_QUERY_LIMIT = 5000
    _DEFAULT_BATCH_SIZE = 250

    def __init__(self, database: Database):
        self._database = database

    def bootstrap(self) -> None:
        self._database.create_tables(BaseCookieChecker)

    def upsert_account(self, payload: AccountUpsertInput | dict[str, Any]) -> dict[str, Any]:
        item = _validate_model(AccountUpsertInput, payload)
        with self._database.session_scope() as session:
            account, created, cookies_added = self._upsert_account_in_session(session, item)
            session.flush()
            return {
                'id': account.id,
                'created': created,
                'cookies_added': cookies_added,
                'account': self._serialize_account(account),
            }

    def upsert_accounts(
        self,
        payload: AccountBatchUpsertInput | Sequence[AccountUpsertInput | dict[str, Any]],
    ) -> dict[str, int]:
        if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
            items = [_validate_model(AccountUpsertInput, item) for item in payload]
            batch_size = self._DEFAULT_BATCH_SIZE
        else:
            batch = _validate_model(AccountBatchUpsertInput, payload)
            items = batch.items
            batch_size = max(1, int(batch.batch_size or self._DEFAULT_BATCH_SIZE))

        created_count = 0
        updated_count = 0
        cookies_added_count = 0

        with self._database.session_scope() as session:
            for index, item in enumerate(items, start=1):
                _account, created, cookies_added = self._upsert_account_in_session(session, item)
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                cookies_added_count += cookies_added

                if index % batch_size == 0:
                    session.flush()
            session.flush()

        return {
            'processed': len(items),
            'created': created_count,
            'updated': updated_count,
            'cookies_added': cookies_added_count,
        }

    def append_cookies(self, payload: CookieAppendInput | dict[str, Any]) -> dict[str, Any]:
        item = _validate_model(CookieAppendInput, payload)
        lookup = self._sanitize_lookup(item.lookup)
        cookies = self._normalize_cookies(item.cookies)
        if not cookies:
            return {'matched': False, 'cookies_added': 0}

        with self._database.session_scope() as session:
            account = self._find_account(session, lookup)
            if account is None:
                return {'matched': False, 'cookies_added': 0}

            cookies_added = account.merge_cookies(cookies)
            session.flush()
            return {'matched': True, 'cookies_added': cookies_added, 'id': account.id}

    def query_accounts(self, payload: AccountQueryInput | dict[str, Any]) -> list[dict[str, Any]]:
        query = _validate_model(AccountQueryInput, payload)
        filters = self._sanitize_filter_fields(query.filters)
        fields = self._sanitize_projection_fields(query.fields)
        limit = max(1, min(int(query.limit), self._MAX_QUERY_LIMIT))
        offset = max(0, int(query.offset))

        with self._database.session_scope() as session:
            stmt = select(Account)
            for field, value in filters.items():
                stmt = stmt.where(getattr(Account, field) == value)

            if query.order_by:
                order_field = str(query.order_by)
                if order_field not in self._ALL_ACCOUNT_FIELDS:
                    raise ValueError(f'Unsupported order_by field: {order_field}')
                column = getattr(Account, order_field)
                stmt = stmt.order_by(column.desc() if query.descending else column.asc())

            stmt = stmt.offset(offset).limit(limit)
            accounts = session.execute(stmt).scalars().all()
            return [
                self._serialize_account(account, fields=fields, include_cookies=query.include_cookies)
                for account in accounts
            ]

    def account_exists(self, **filters: Any) -> bool:
        with self._database.session_scope() as session:
            safe_filters = self._sanitize_filter_fields(filters)
            return self._database.record_exists(session, Account, **safe_filters)

    def _upsert_account_in_session(
        self,
        session: Session,
        item: AccountUpsertInput,
    ) -> tuple[Account, bool, int]:
        lookup = self._sanitize_lookup(item.lookup)
        values = self._sanitize_mutable_fields(item.values)
        cookies = self._normalize_cookies(item.cookies, values.get('p_cookie'))
        values.pop('p_cookie', None)

        account = self._find_account(session, lookup)
        created = account is None

        if created:
            create_values = {k: v for k, v in lookup.items() if k in self._MUTABLE_ACCOUNT_FIELDS}
            create_values.update(values)
            account = Account(**create_values)
            session.add(account)
        else:
            for field, value in values.items():
                setattr(account, field, value)

        cookies_added = account.merge_cookies(cookies)
        return account, created, cookies_added

    def _find_account(self, session: Session, lookup: dict[str, Any]) -> Account | None:
        stmt = select(Account)
        for field, value in lookup.items():
            stmt = stmt.where(getattr(Account, field) == value)
        return session.execute(stmt.limit(1)).scalar_one_or_none()

    def _sanitize_lookup(self, lookup: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(lookup, dict):
            raise ValueError('lookup must be a dictionary')

        safe_lookup: dict[str, Any] = {}
        for field, value in lookup.items():
            if field not in self._LOOKUP_FIELDS:
                raise ValueError(f'Unsupported lookup field: {field}')
            if value is None or value == '':
                continue
            safe_lookup[field] = value

        if not safe_lookup:
            raise ValueError('lookup must contain at least one supported non-empty field')
        return safe_lookup

    def _sanitize_filter_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(fields, dict):
            raise ValueError('filters must be a dictionary')

        safe_filters: dict[str, Any] = {}
        for field, value in fields.items():
            if field not in self._ALL_ACCOUNT_FIELDS:
                raise ValueError(f'Unsupported filter field: {field}')
            safe_filters[field] = value
        return safe_filters

    def _sanitize_mutable_fields(self, values: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(values, dict):
            raise ValueError('values must be a dictionary')

        safe_values: dict[str, Any] = {}
        for field, value in values.items():
            if field not in self._MUTABLE_ACCOUNT_FIELDS:
                raise ValueError(f'Unsupported mutable field: {field}')
            safe_values[field] = value
        return safe_values

    def _sanitize_projection_fields(self, fields: list[str] | None) -> set[str] | None:
        if fields is None:
            return None
        if not isinstance(fields, list):
            raise ValueError('fields must be a list of account fields')

        safe_fields: set[str] = set()
        for field in fields:
            if field not in self._ALL_ACCOUNT_FIELDS:
                raise ValueError(f'Unsupported projection field: {field}')
            safe_fields.add(field)
        return safe_fields

    @staticmethod
    def _normalize_cookies(*cookie_sources: Any) -> set[str]:
        result: set[str] = set()
        for source in cookie_sources:
            if source is None:
                continue

            if isinstance(source, str):
                cookie = source.strip()
                if cookie:
                    result.add(cookie)
                continue

            if isinstance(source, Iterable):
                for item in source:
                    cookie = str(item).strip()
                    if cookie:
                        result.add(cookie)
                continue

            cookie = str(source).strip()
            if cookie:
                result.add(cookie)
        return result

    def _serialize_account(
        self,
        account: Account,
        *,
        fields: set[str] | None = None,
        include_cookies: bool = True,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for column in Account.__table__.columns:
            if fields is not None and column.name not in fields:
                continue

            value = getattr(account, column.name)
            if column.name == 'p_cookie':
                if include_cookies:
                    data[column.name] = sorted(account.cookies())
                continue
            data[column.name] = value

        if include_cookies and (fields is None or 'p_cookie' in fields):
            data['p_cookie'] = sorted(account.cookies())
        return data
