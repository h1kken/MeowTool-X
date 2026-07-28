from __future__ import annotations

import threading
from time import time
import typing as t

from pypresence.exceptions import DiscordError, DiscordNotFound, InvalidPipe, PipeClosed
from pypresence.presence import Presence
from pypresence.types import ActivityType

from src.app.constants import PROGRAM_NAME
from src.config.enums import ConfigKey as CKey
from src.ui.types import PageState
from src.utils.logging import logger

if t.TYPE_CHECKING:
    from src.config.manager import Config
    from src.ui.windows.main_window import MainWindow


class DiscordRPC:
    APP_ID = "1493918950344626216"

    DEFAULT_PAGE = "Startup"
    
    RETRY_DELAY_SECONDS = 5.0

    ACTIVITY_TYPE = ActivityType.PLAYING
    NAME = PROGRAM_NAME
    # LARGE_IMAGE = None
    # LARGE_TEXT = None
    # SMALL_IMAGE = None
    # SMALL_TEXT = None

    def __init__(self, window: MainWindow, config: Config) -> None:
        self._config = config
        
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None

        self._enabled = self._read_enabled()
        self._state = self._normalize_state(window.current_state())
        self._started_at = int(time())

        window.page_changed.connect(self._set_state)
        config.config_loaded.connect(self._load_config)
        config.value_changed.connect(self._on_config_changed)

    def start(self) -> None:
        with self._lock:
            if self._worker is not None and self._worker.is_alive():
                return

            self._started_at = int(time())
            self._stop.clear()
            self._wake.clear()
            
            self._worker = threading.Thread(
                target=self._run,
                name="DiscordRPC",
                daemon=True,
            )

        self._worker.start()

    def shutdown(self) -> None:
        self._stop.set()
        self._wake.set()

        worker = self._worker
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=3.0)

        if worker is None or not worker.is_alive():
            self._worker = None

    def _read_enabled(self) -> bool:
        return bool(self._config.get(CKey.OUTPUTS_DISCORD_RICH_PRESENCE))

    def _load_config(self) -> None:
        self._set_enabled(self._read_enabled())

    def _on_config_changed(self, key: str, _value: object) -> None:
        if key == CKey.OUTPUTS_DISCORD_RICH_PRESENCE:
            self._load_config()

    def _set_enabled(self, enabled: bool) -> None:
        with self._lock:
            if enabled == self._enabled:
                return

            self._enabled = enabled
            if enabled:
                self._started_at = int(time())

        self._wake.set()

    def _set_state(self, state: PageState) -> None:
        state = self._normalize_state(state)
        with self._lock:
            if state == self._state:
                return
            self._state = state

        self._wake.set()

    @classmethod
    def _normalize_state(cls, state: PageState) -> PageState:
        main = state.get("main", "") or cls.DEFAULT_PAGE
        new_state: PageState = {"main": main}

        raw_inner = state.get("inner")
        if isinstance(raw_inner, tuple):
            inner = tuple(part for part in (item for item in raw_inner) if part)
            if inner:
                new_state["inner"] = inner

        return new_state

    def _snapshot(self) -> tuple[bool, PageState, int]:
        with self._lock:
            return self._enabled, self._state, self._started_at

    @staticmethod
    def _format_page(page: PageState) -> str:
        main = page["main"]
        inner = page.get("inner")
        if inner:
            return f"{main}: {' > '.join(inner)}"
        return main

    def _connect(self) -> Presence | None:
        for pipe in range(10):
            rpc: Presence | None = None
            try:
                rpc = Presence(self.APP_ID, pipe=pipe)
                rpc.connect()
                logger.info(f"Discord Presence connected (pipe {pipe})")
                return rpc
            except (DiscordNotFound, InvalidPipe, PipeClosed, OSError):
                self._disconnect(rpc, clear=False)
            except DiscordError as e:
                self._disconnect(rpc, clear=False)
                logger.warning(f"Discord Presence connection failed: {e}")
                return None
            except Exception as e:
                self._disconnect(rpc, clear=False)
                logger.exception(f"Discord Presence connection failed: {e}")
                return None

        return None

    @staticmethod
    def _disconnect(rpc: Presence | None, *, clear: bool = True) -> None:
        if rpc is None:
            return

        if clear:
            try:
                rpc.clear()
            except Exception:
                pass

        try:
            rpc.close()
        except Exception:
            try:
                rpc.loop.close() # pyright: ignore[reportUnknownMemberType]
            except Exception:
                pass

    def _run(self) -> None:
        rpc: Presence | None = None

        try:
            while not self._stop.is_set():
                self._wake.clear()
                enabled, page, started_at = self._snapshot()

                if not enabled:
                    if rpc is not None:
                        self._disconnect(rpc)
                        rpc = None
                        logger.debug("Discord Presence disconnected")
                    self._wake.wait()
                    continue

                if rpc is None:
                    rpc = self._connect()
                    if rpc is None:
                        self._wake.wait(self.RETRY_DELAY_SECONDS)
                    continue

                try:
                    self._update(rpc, page, started_at)
                except (DiscordNotFound, InvalidPipe, PipeClosed, BrokenPipeError, OSError):
                    self._disconnect(rpc, clear=False)
                    rpc = None
                    self._wake.wait(self.RETRY_DELAY_SECONDS)
                    continue
                except Exception as e:
                    logger.exception(f"Discord Presence update failed: {e}")
                    self._disconnect(rpc, clear=False)
                    rpc = None
                    self._wake.wait(self.RETRY_DELAY_SECONDS)
                    continue

                self._wake.wait()
        finally:
            if rpc is not None:
                self._disconnect(rpc)
                logger.debug("Discord Presence disconnected")

    def _update(self, rpc: Presence, page: PageState, started_at: int) -> None:
        details = self._format_page(page)
        rpc.update( # pyright: ignore[reportUnknownMemberType]
            start=max(1, started_at),
            
            activity_type=self.ACTIVITY_TYPE,
            name=self.NAME,
            details=details,
            
            # large_image=self.LARGE_IMAGE,
            # large_text=self.LARGE_TEXT,
            # small_image=self.SMALL_IMAGE,
            # small_text=self.SMALL_TEXT,
        )
