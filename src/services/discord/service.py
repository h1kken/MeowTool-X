from __future__ import annotations

import os
import threading
from time import time
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject

from src.utils.logging import logger
from src.services.discord.constants import ( # TODO: remove
    DISCORD_RPC_LARGE_IMAGE_KEY,
    DISCORD_RPC_SMALL_IMAGE_KEY,
    DISCORD_RPC_SMALL_IMAGE_TEXT,
)

if TYPE_CHECKING:
    from src.ui.windows.main_window import MainWindow
    from src.config.manager import Config


class _DiscordRPCImportError(Exception):
    pass


try:
    from pypresence.exceptions import DiscordError, DiscordNotFound, InvalidPipe, PipeClosed
    from pypresence.presence import Presence
    from pypresence.types import ActivityType
except Exception:  # pragma: no cover - optional dependency safety
    Presence = None
    ActivityType = None
    DiscordError = DiscordNotFound = InvalidPipe = PipeClosed = _DiscordRPCImportError


class DiscordRPC(QObject):
    APP_ID = '1493918950344626216'
    
    DEFAULT_PAGE = "Startup"
    RETRY_DELAY_SECONDS = 5.0
    CAPACITY_DELAY_SECONDS = 15.0

    def __init__(self, window: MainWindow, config: Config) -> None:
        super().__init__(window)
        self._window = window
        self._config = config
        
        self._started_at = int(time())
        self._page = self._normalize_page(window.current_presence_page())
        self._enabled = False
        self._preferred_pipe = 0
        self._capacity_logged = False

        self._state_lock = threading.Lock()
        self._wake_event = threading.Event()
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None

        self._window.presence_page_changed.connect(self._set_page)
        config.config_loaded.connect(self._sync_enabled)
        config.value_changed.connect(self._on_config_value_changed)

    def start(self) -> None:
        self._started_at = int(time())
        self._start_worker()
        self._sync_enabled()
        self._request_refresh()

    def shutdown(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=3.0)
        self._worker = None

    def _start_worker(self) -> None:
        worker = self._worker
        if worker is not None and worker.is_alive():
            return

        self._stop_event.clear()
        self._wake_event.clear()
        self._worker = threading.Thread(
            target=self._worker_loop,
            name="DiscordRPCWorker",
            daemon=True,
        )
        self._worker.start()

    def _on_config_value_changed(self, key: str, _value: object) -> None:
        if str(key).strip() != self.CONFIG_KEY:
            return
        self._sync_enabled()

    def _sync_enabled(self, *_args: object) -> None:
        enabled = bool(self._config.get(self.CONFIG_KEY, default=False))
        with self._state_lock:
            changed = enabled != self._enabled
            self._enabled = enabled
            if enabled and changed:
                self._started_at = int(time())
        self._request_refresh()

    def _set_page(self, page: str) -> None:
        normalized = self._normalize_page(page)
        with self._state_lock:
            if normalized == self._page:
                return
            self._page = normalized
        self._request_refresh()

    def _request_refresh(self) -> None:
        self._wake_event.set()

    @classmethod
    def _normalize_page(cls, page: str) -> str:
        return str(page).strip() or cls.DEFAULT_PAGE

    def _snapshot(self) -> tuple[bool, str, int]:
        with self._state_lock:
            return self._enabled, self._page, self._started_at

    def _build_payload(self, page: str, started_at: int) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "pid": os.getpid(),
            "start": max(1, int(started_at)),
        }

        details = self._normalize_page(page)[:128]
        if details:
            payload["details"] = details

        if ActivityType is not None:
            payload["activity_type"] = ActivityType.PLAYING

        large_image = str(DISCORD_RPC_LARGE_IMAGE_KEY).strip()
        if large_image:
            payload["large_image"] = large_image

        small_image = str(DISCORD_RPC_SMALL_IMAGE_KEY).strip()
        if small_image:
            payload["small_image"] = small_image
            small_text = str(DISCORD_RPC_SMALL_IMAGE_TEXT).strip()
            if small_text:
                payload["small_text"] = small_text[:128]

        return payload

    @staticmethod
    def _signature(payload: dict[str, Any]) -> tuple[tuple[str, str], ...]:
        return tuple((key, repr(payload[key])) for key in sorted(payload))

    def _connect(self) -> tuple[object | None, float]:
        if not self.APP_ID:
            logger.warning("Discord Presence is enabled, but DISCORD_PRESENCE_APP_ID is empty.")
            return None, self.RETRY_DELAY_SECONDS

        if Presence is None:
            logger.warning("Discord Presence is enabled, but pypresence is not installed.")
            return None, self.RETRY_DELAY_SECONDS

        for pipe in [self._preferred_pipe, *[value for value in range(10) if value != self._preferred_pipe]]:
            rpc: object | None = None
            try:
                rpc = Presence(self.APP_ID, pipe=pipe)
                rpc.connect()
                self._preferred_pipe = pipe
                self._capacity_logged = False
                logger.info(f"Discord Presence connected (pipe {pipe})")
                return rpc, self.RETRY_DELAY_SECONDS
            except DiscordError as exc:
                self._close_rpc(rpc)
                if getattr(exc, "code", None) == 1006 or "Server at capacity" in str(exc):
                    if not self._capacity_logged:
                        logger.warning("Discord Presence temporarily unavailable: Discord server at capacity.")
                        self._capacity_logged = True
                    return None, self.CAPACITY_DELAY_SECONDS
            except (DiscordNotFound, InvalidPipe, OSError):
                self._close_rpc(rpc)
                continue
            except Exception as exc:  # pragma: no cover - defensive guard
                self._close_rpc(rpc)
                logger.exception(f"Discord Presence connection failed. Error: {exc}")
                return None, self.RETRY_DELAY_SECONDS

        return None, self.RETRY_DELAY_SECONDS

    def _update(self, rpc: object, payload: dict[str, Any]) -> bool:
        try:
            getattr(rpc, "update")(**payload)
            return True
        except (DiscordNotFound, InvalidPipe, PipeClosed, BrokenPipeError, OSError):
            logger.debug("Discord Presence update skipped: pipe unavailable")
            return False
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception(f"Discord Presence update failed. Error: {exc}")
            return False

    def _close_rpc(self, rpc: object | None) -> None:
        if rpc is None:
            return

        try:
            getattr(rpc, "clear")(pid=os.getpid())
        except Exception:
            pass

        try:
            getattr(rpc, "close")()
        except Exception:
            pass

        loop = getattr(rpc, "loop", None)
        if loop is None:
            return

        try:
            if not loop.is_closed():
                loop.close()
        except Exception:
            pass

    def _wait(self, timeout: float | None = None) -> None:
        self._wake_event.wait(timeout)
        self._wake_event.clear()

    def _worker_loop(self) -> None:
        rpc: object | None = None
        last_signature: tuple[tuple[str, str], ...] | None = None
        retry_delay = self.RETRY_DELAY_SECONDS

        while not self._stop_event.is_set():
            enabled, page, started_at = self._snapshot()

            if not enabled:
                last_signature = None
                if rpc is not None:
                    self._close_rpc(rpc)
                    rpc = None
                    logger.debug("Discord Presence disconnected")
                self._wait()
                continue

            if rpc is None:
                rpc, retry_delay = self._connect()
                if rpc is None:
                    self._wait(retry_delay)
                    continue
                last_signature = None

            payload = self._build_payload(page, started_at)
            signature = self._signature(payload)

            if signature == last_signature:
                self._wait()
                continue

            if Presence is not None:
                # self._update(rpc, payload):
                last_signature = signature
                self._wait()
                continue

            self._close_rpc(rpc)
            rpc = None
            last_signature = None
            self._wait(self.RETRY_DELAY_SECONDS)

        if rpc is not None:
            self._close_rpc(rpc)
            logger.debug("Discord Presence disconnected")
