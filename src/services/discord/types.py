from __future__ import annotations

from asyncio import AbstractEventLoop
from typing import Any, Protocol

type PresencePayload = dict[str, Any]
type PresenceState = dict[str, Any]


class RpcClient(Protocol):
    loop: AbstractEventLoop | None

    def connect(self) -> None: ...
    def clear(self, *args: Any, **kwargs: Any) -> Any: ...
    def close(self) -> None: ...
    def update(self, *args: Any, **kwargs: Any) -> Any: ...


__all__ = ("PresencePayload", "PresenceState", "RpcClient")
