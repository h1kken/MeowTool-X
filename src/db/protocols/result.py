import typing as t

from sqlalchemy.orm import InstrumentedAttribute


class ResultModelProtocol(t.Protocol):
    id: t.ClassVar[InstrumentedAttribute[int]]
