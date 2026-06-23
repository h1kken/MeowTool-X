from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Protocol


def _empty_str_dict() -> dict[str, str]:
    return {}


type JsonObject = dict[str, Any]


class NativeHttpHandleProtocol(Protocol):
    def __init__(
        self,
        proxies: list[JsonObject] | None,
        config: JsonObject | None,
        *,
        debug_hook: Callable[[str, str, str], None] | None = None,
    ) -> None: ...

    def run_batch(self, requests: list[JsonObject]) -> Iterable[JsonObject]: ...
    def submit_batch(self, requests: list[JsonObject]) -> int: ...
    def get_stats(self) -> JsonObject: ...
    def reset_stats(self) -> None: ...
    def update_proxies(self, proxies: list[JsonObject]) -> None: ...
    def poll_batch(self, batch_id: int, max_items: int | None = None) -> JsonObject: ...
    def get_batch_status(self, batch_id: int) -> JsonObject: ...
    def cancel_batch(self, batch_id: int) -> None: ...
    def cleanup_batch(self, batch_id: int) -> bool: ...
    def close(self) -> None: ...
    def is_closed(self) -> bool: ...


class NativeHttpModuleProtocol(Protocol):
    NativeHttpEngineHandle: type[NativeHttpHandleProtocol]

    def version(self) -> str: ...


@dataclass(slots=True)
class NativeHttpEngineConfig:
    connect_timeout_ms: int = 5_000
    request_timeout_ms: int = 15_000
    proxy_cooldown_429_ms: int = 30_000
    proxy_cooldown_transport_ms: int = 10_000
    proxy_cooldown_5xx_ms: int = 0
    concurrency_profile: str = "auto"
    per_proxy_max_in_flight: int | None = None
    direct_max_in_flight: int | None = None
    max_concurrency: int | None = None
    capture_text_body: bool = False
    response_body_mode: str = "none"
    max_response_bytes: int | None = 262_144
    preview_response_bytes: int | None = 4_096
    max_retries: int | None = 0
    retry_backoff_ms: int = 0
    retry_on_429: bool = True
    retry_429_forever: bool = False
    retry_on_transport_error: bool = True
    retry_on_5xx: bool = False
    debug_logging: bool | None = None
    debug_log_response_body: bool | None = None
    debug_body_preview_chars: int = 256
    allow_direct_fallback: bool = False
    danger_accept_invalid_certs: bool = False
    default_headers: dict[str, str] = field(default_factory=_empty_str_dict)
    user_agent: str | None = None


@dataclass(slots=True)
class NativeProxySpec:
    url: str
    id: str | None = None


@dataclass(slots=True)
class NativeHttpRequest:
    request_id: str
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=_empty_str_dict)
    params: dict[str, str] = field(default_factory=_empty_str_dict)
    body: str | None = None
    body_bytes: bytes | None = None
    json_body: Any = None
    timeout_ms: int | None = None


@dataclass(slots=True)
class NativeHttpChunkOptions:
    chunk_size: int = 1_000
    flatten: bool = True


type ProxyLike = JsonObject | str | NativeProxySpec
type RequestLike = JsonObject | NativeHttpRequest

__all__ = (
    "JsonObject",
    "NativeHttpChunkOptions",
    "NativeHttpEngineConfig",
    "NativeHttpHandleProtocol",
    "NativeHttpModuleProtocol",
    "NativeHttpRequest",
    "NativeProxySpec",
    "ProxyLike",
    "RequestLike",
)
