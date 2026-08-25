import typing as t

from sqlalchemy.orm import InstrumentedAttribute


class RunModelProtocol(t.Protocol):
    id: t.ClassVar[InstrumentedAttribute[int]]
