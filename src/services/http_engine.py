from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Callable, Iterable, Iterator, Sequence

from src.utils.constants import IS_LAUNCHED_WITH_CONSOLE
from src.utils.logging import logger


class NativeHttpEngineUnavailable(RuntimeError):
    pass


CONCURRENCY_PRESETS: dict[str, dict[str, int]] = {
    "auto": {
        "max_concurrency": 64,
        "per_proxy_max_in_flight": 8,
        "direct_max_in_flight": 2,
    },
    "low": {
        "max_concurrency": 16,
        "per_proxy_max_in_flight": 2,
        "direct_max_in_flight": 1,
    },
    "balanced": {
        "max_concurrency": 64,
        "per_proxy_max_in_flight": 8,
        "direct_max_in_flight": 2,
    },
    "high": {
        "max_concurrency": 128,
        "per_proxy_max_in_flight": 16,
        "direct_max_in_flight": 4,
    },
}

APP_CONFIG_DEFAULTS = {
    "concurrency_profile": "Auto",
    "max_concurrency": 64,
    "per_proxy_max_in_flight": 8,
    "direct_max_in_flight": 2,
}


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
    default_headers: dict[str, str] = field(default_factory=dict)
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
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    body_bytes: bytes | None = None
    json_body: Any = None
    timeout_ms: int | None = None


@dataclass(slots=True)
class NativeHttpChunkOptions:
    chunk_size: int = 1_000
    flatten: bool = True


class NativeHttpSubmission:
    def __init__(self, engine: NativeHttpEngine, batch_id: int) -> None:
        self._engine = engine
        self.batch_id = int(batch_id)

    def poll(self, *, max_items: int | None = None) -> dict[str, Any]:
        return self._engine.poll_batch(self.batch_id, max_items=max_items)

    def status(self) -> dict[str, Any]:
        return self._engine.get_batch_status(self.batch_id)

    def wait(
        self,
        *,
        poll_interval_ms: int = 10,
        max_items_per_poll: int | None = None,
    ) -> list[dict[str, Any]]:
        return self._engine.wait_batch(
            self.batch_id,
            poll_interval_ms=poll_interval_ms,
            max_items_per_poll=max_items_per_poll,
        )

    def cancel(self) -> None:
        self._engine.cancel_batch(self.batch_id)

    def cleanup(self) -> bool:
        return self._engine.cleanup_batch(self.batch_id)


class NativeHttpEngine:
    def __init__(
        self,
        *,
        proxies: Sequence[dict[str, Any] | str | NativeProxySpec] | None = None,
        config: NativeHttpEngineConfig | dict[str, Any] | None = None,
    ) -> None:
        native = _import_native_module()
        payload_proxies = None if proxies is None else _normalize_proxies(proxies)
        payload_config = None if config is None else _normalize_config(config)
        debug_hook = (
            _native_debug_log_hook if payload_config.get("debug_logging") else None
        )
        self._native = native.NativeHttpEngineHandle(
            payload_proxies, payload_config, debug_hook=debug_hook
        )

    def run_batch(
        self, requests: Sequence[dict[str, Any] | NativeHttpRequest]
    ) -> list[dict[str, Any]]:
        return list(self._native.run_batch(_normalize_requests(requests)))

    def submit_batch(
        self, requests: Sequence[dict[str, Any] | NativeHttpRequest]
    ) -> NativeHttpSubmission:
        batch_id = int(self._native.submit_batch(_normalize_requests(requests)))
        return NativeHttpSubmission(self, batch_id)

    def iter_chunked(
        self,
        requests: Sequence[dict[str, Any] | NativeHttpRequest]
        | Iterable[dict[str, Any] | NativeHttpRequest],
        *,
        chunk_size: int = 1_000,
    ) -> Iterator[list[dict[str, Any]]]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")

        buffer: list[dict[str, Any]] = []
        for request in requests:
            buffer.append(_normalize_request(request))
            if len(buffer) >= chunk_size:
                yield self.run_batch(buffer)
                buffer.clear()

        if buffer:
            yield self.run_batch(buffer)

    def run_chunked(
        self,
        requests: Sequence[dict[str, Any] | NativeHttpRequest]
        | Iterable[dict[str, Any] | NativeHttpRequest],
        *,
        chunk_size: int = 1_000,
        flatten: bool = True,
        on_chunk: Callable[[list[dict[str, Any]]], Any] | None = None,
    ) -> list[dict[str, Any]] | list[list[dict[str, Any]]]:
        collected: list[Any] = []
        for chunk in self.iter_chunked(requests, chunk_size=chunk_size):
            if callable(on_chunk):
                on_chunk(chunk)
            if flatten:
                collected.extend(chunk)
            else:
                collected.append(chunk)
        return collected

    def get_stats(self) -> dict[str, Any]:
        return dict(self._native.get_stats())

    def reset_stats(self) -> None:
        self._native.reset_stats()

    def update_proxies(
        self, proxies: Sequence[dict[str, Any] | str | NativeProxySpec]
    ) -> None:
        self._native.update_proxies(_normalize_proxies(proxies))

    def poll_batch(
        self, batch_id: int, *, max_items: int | None = None
    ) -> dict[str, Any]:
        if max_items is None:
            raw = dict(self._native.poll_batch(int(batch_id)))
        else:
            raw = dict(self._native.poll_batch(int(batch_id), int(max_items)))
        ready = list(raw.pop("ready", []) or [])
        return {
            "status": raw,
            "ready": ready,
        }

    def get_batch_status(self, batch_id: int) -> dict[str, Any]:
        return dict(self._native.get_batch_status(int(batch_id)))

    def wait_batch(
        self,
        batch_id: int,
        *,
        poll_interval_ms: int = 10,
        max_items_per_poll: int | None = None,
    ) -> list[dict[str, Any]]:
        import time

        interval = max(0.0, float(poll_interval_ms) / 1000.0)
        collected: list[dict[str, Any]] = []
        while True:
            polled = self.poll_batch(batch_id, max_items=max_items_per_poll)
            ready = polled.get("ready") or []
            if ready:
                collected.extend(ready)
            status = polled.get("status") or {}
            if bool(status.get("done")):
                return collected
            if interval > 0:
                time.sleep(interval)

    def cancel_batch(self, batch_id: int) -> None:
        self._native.cancel_batch(int(batch_id))

    def cleanup_batch(self, batch_id: int) -> bool:
        return bool(self._native.cleanup_batch(int(batch_id)))

    def close(self) -> None:
        self._native.close()

    def is_closed(self) -> bool:
        return bool(self._native.is_closed())

    def __enter__(self) -> NativeHttpEngine:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class NativeHttpBatchRunner:
    def __init__(self, engine: NativeHttpEngine, *, chunk_size: int = 1_000) -> None:
        self._engine = engine
        self._chunk_size = max(1, int(chunk_size))

    def run(
        self,
        requests: Sequence[dict[str, Any] | NativeHttpRequest]
        | Iterable[dict[str, Any] | NativeHttpRequest],
        *,
        flatten: bool = True,
        on_chunk: Callable[[list[dict[str, Any]]], Any] | None = None,
    ) -> list[dict[str, Any]] | list[list[dict[str, Any]]]:
        return self._engine.run_chunked(
            requests,
            chunk_size=self._chunk_size,
            flatten=flatten,
            on_chunk=on_chunk,
        )

    def iter_chunks(
        self,
        requests: Sequence[dict[str, Any] | NativeHttpRequest]
        | Iterable[dict[str, Any] | NativeHttpRequest],
    ) -> Iterator[list[dict[str, Any]]]:
        return self._engine.iter_chunked(requests, chunk_size=self._chunk_size)


def create_engine(
    *,
    proxies: Sequence[dict[str, Any] | str | NativeProxySpec] | None = None,
    config: NativeHttpEngineConfig | dict[str, Any] | None = None,
) -> NativeHttpEngine:
    return NativeHttpEngine(proxies=proxies, config=config)


def create_batch_runner(
    engine: NativeHttpEngine, *, chunk_size: int = 1_000
) -> NativeHttpBatchRunner:
    return NativeHttpBatchRunner(engine, chunk_size=chunk_size)


def build_config_from_app_config(
    config_source: Any | None = None,
    **overrides: Any,
) -> NativeHttpEngineConfig:
    if config_source is None:
        from src.config.manager import config as config_source

    values = {
        "concurrency_profile": str(
            config_source.get(
                "HTTP Engine>Concurrency Profile",
                default=APP_CONFIG_DEFAULTS["concurrency_profile"],
            )
        ).strip()
        or APP_CONFIG_DEFAULTS["concurrency_profile"],
        "max_concurrency": int(
            config_source.get(
                "HTTP Engine>Max Concurrency",
                default=APP_CONFIG_DEFAULTS["max_concurrency"],
            )
        ),
        "per_proxy_max_in_flight": int(
            config_source.get(
                "HTTP Engine>Per Proxy Max In Flight",
                default=APP_CONFIG_DEFAULTS["per_proxy_max_in_flight"],
            )
        ),
        "direct_max_in_flight": int(
            config_source.get(
                "HTTP Engine>Direct Max In Flight",
                default=APP_CONFIG_DEFAULTS["direct_max_in_flight"],
            )
        ),
    }
    values.update(overrides)
    return NativeHttpEngineConfig(**values)


def is_available() -> bool:
    try:
        _import_native_module()
    except NativeHttpEngineUnavailable:
        return False
    return True


def run_batch(
    requests: Sequence[dict[str, Any] | NativeHttpRequest],
    *,
    proxies: Sequence[dict[str, Any] | str | NativeProxySpec] | None = None,
    config: NativeHttpEngineConfig | dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    with create_engine(proxies=proxies, config=config) as engine:
        return engine.run_batch(requests)


def run_chunked(
    requests: Sequence[dict[str, Any] | NativeHttpRequest]
    | Iterable[dict[str, Any] | NativeHttpRequest],
    *,
    proxies: Sequence[dict[str, Any] | str | NativeProxySpec] | None = None,
    config: NativeHttpEngineConfig | dict[str, Any] | None = None,
    chunk_size: int = 1_000,
    flatten: bool = True,
    on_chunk: Callable[[list[dict[str, Any]]], Any] | None = None,
) -> list[dict[str, Any]] | list[list[dict[str, Any]]]:
    with create_engine(proxies=proxies, config=config) as engine:
        return engine.run_chunked(
            requests, chunk_size=chunk_size, flatten=flatten, on_chunk=on_chunk
        )


def version() -> str:
    native = _import_native_module()
    return str(native.version())


def get_concurrency_presets() -> dict[str, dict[str, int]]:
    return {name: values.copy() for name, values in CONCURRENCY_PRESETS.items()}


def build_instructions() -> str:
    return (
        "Rust module is not built yet. Install rustup + maturin, then run:\n"
        "cd native/http_engine\n"
        "maturin develop --release"
    )


def _import_native_module():
    try:
        import meowtool_native_http

        if hasattr(meowtool_native_http, "NativeHttpEngineHandle"):
            return meowtool_native_http
        import meowtool_native_http.meowtool_native_http as native_impl

        return native_impl
    except (
        Exception
    ) as error:  # pragma: no cover - import depends on local native build
        raise NativeHttpEngineUnavailable(build_instructions()) from error


def _normalize_config(
    config: NativeHttpEngineConfig | dict[str, Any],
) -> dict[str, Any]:
    normalized = asdict(config) if is_dataclass(config) else dict(config)
    if normalized.get("debug_logging") is None:
        normalized["debug_logging"] = IS_LAUNCHED_WITH_CONSOLE
    if normalized.get("debug_log_response_body") is None:
        normalized["debug_log_response_body"] = IS_LAUNCHED_WITH_CONSOLE
    _apply_concurrency_profile(normalized)
    body_mode = normalized.pop("response_body_mode", None)
    if body_mode:
        normalized["body_mode"] = body_mode
    elif normalized.get("capture_text_body") and not normalized.get("body_mode"):
        normalized["body_mode"] = "text"
    return normalized


def _apply_concurrency_profile(normalized: dict[str, Any]) -> None:
    raw_profile = normalized.pop("concurrency_profile", "auto")
    profile = str(raw_profile or "auto").strip().lower()
    if profile == "custom":
        return

    preset = CONCURRENCY_PRESETS.get(profile)
    if preset is None:
        raise ValueError(
            "concurrency_profile must be one of: auto, low, balanced, high, custom"
        )

    for key, value in preset.items():
        if normalized.get(key) is None:
            normalized[key] = value


def _normalize_proxies(
    proxies: Sequence[dict[str, Any] | str | NativeProxySpec],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for proxy in proxies:
        if isinstance(proxy, str):
            normalized.append({"url": proxy})
        elif is_dataclass(proxy):
            normalized.append(asdict(proxy))
        else:
            normalized.append(dict(proxy))
    return normalized


def _normalize_request(request: dict[str, Any] | NativeHttpRequest) -> dict[str, Any]:
    if is_dataclass(request):
        return asdict(request)
    return dict(request)


def _normalize_requests(
    requests: Sequence[dict[str, Any] | NativeHttpRequest],
) -> list[dict[str, Any]]:
    return [_normalize_request(request) for request in requests]


def _native_debug_log_hook(level: str, event: str, message: str) -> None:
    with logger.origin_scope("native.http_engine:-", overwrite=True):
        line = f"[{event}] {message}"
        level_name = (level or "debug").strip().lower()
        if level_name == "info":
            logger.info(line)
        elif level_name in {"warning", "warn"}:
            logger.warning(line)
        elif level_name == "error":
            logger.error(line)
        else:
            logger.debug(line)


__all__ = [
    "NativeHttpBatchRunner",
    "NativeHttpChunkOptions",
    "NativeHttpEngine",
    "NativeHttpEngineConfig",
    "NativeHttpEngineUnavailable",
    "NativeHttpRequest",
    "NativeHttpSubmission",
    "NativeProxySpec",
    "APP_CONFIG_DEFAULTS",
    "build_instructions",
    "build_config_from_app_config",
    "create_batch_runner",
    "create_engine",
    "get_concurrency_presets",
    "is_available",
    "run_batch",
    "run_chunked",
    "version",
]
