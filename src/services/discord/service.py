from __future__ import annotations

import os
import threading
from time import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject
from pypresence.exceptions import DiscordError, DiscordNotFound, InvalidPipe, PipeClosed
from pypresence.presence import Presence
from pypresence.types import ActivityType

from src.config.enums import ConfigKey
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.config.manager import Config
    from src.ui.windows.main_window import MainWindow


class DiscordRPC(QObject):
    APP_ID = "1493918950344626216"
    CONFIG_KEY = ConfigKey.OUTPUTS_DISCORD_RICH_PRESENCE

    DEFAULT_PAGE = "Startup"
    RETRY_DELAY_SECONDS = 5.0
    TEXT_LIMIT = 128

    LARGE_IMAGE = ""
    LARGE_TEXT = "MeowTool X"
    SMALL_IMAGE = ""
    SMALL_TEXT = ""

    def __init__(self, window: MainWindow, config: Config) -> None:
        super().__init__(window)
        self._config = config
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None

        self._enabled = self._read_enabled()
        self._page = self._normalize_page(window.current_presence_page())
        self._started_at = int(time())

        window.presence_page_changed.connect(self._set_page)
        config.config_loaded.connect(self._load_config)
        config.value_changed.connect(self._on_config_changed)

    def start(self) -> None:
        with self._lock:
            if self._worker is not None and self._worker.is_alive():
                return

            self._started_at = int(time())
            self._stop.clear()
            self._wake.clear()
            worker = threading.Thread(
                target=self._run,
                name="DiscordRPC",
                daemon=True,
            )
            self._worker = worker

        worker.start()

    def shutdown(self) -> None:
        self._stop.set()
        self._wake.set()

        worker = self._worker
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=3.0)

        if worker is None or not worker.is_alive():
            self._worker = None

    def _read_enabled(self) -> bool:
        return bool(self._config.get(self.CONFIG_KEY, default=False))

    def _load_config(self) -> None:
        self._set_enabled(self._read_enabled())

    def _on_config_changed(self, key: str, _value: object) -> None:
        if key == self.CONFIG_KEY:
            self._load_config()

    def _set_enabled(self, enabled: bool) -> None:
        with self._lock:
            if enabled == self._enabled:
                return

            self._enabled = enabled
            if enabled:
                self._started_at = int(time())

        self._wake.set()

    def _set_page(self, page: str) -> None:
        page = self._normalize_page(page)
        with self._lock:
            if page == self._page:
                return
            self._page = page

        self._wake.set()

    @classmethod
    def _normalize_page(cls, page: str) -> str:
        return str(page).strip() or cls.DEFAULT_PAGE

    def _snapshot(self) -> tuple[bool, str, int]:
        with self._lock:
            return self._enabled, self._page, self._started_at

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
            except DiscordError as error:
                self._disconnect(rpc, clear=False)
                logger.warning(f"Discord Presence connection failed: {error}")
                return None
            except Exception as error:
                self._disconnect(rpc, clear=False)
                logger.exception(f"Discord Presence connection failed: {error}")
                return None

        return None

    def _update(self, rpc: Presence, page: str, started_at: int) -> None:
        rpc.update(  # pyright: ignore[reportUnknownMemberType]
            pid=os.getpid(),
            activity_type=ActivityType.PLAYING,
            details=page[:self.TEXT_LIMIT],
            start=max(1, started_at),
            large_image=self.LARGE_IMAGE or None,
            large_text=(
                self.LARGE_TEXT[:self.TEXT_LIMIT] if self.LARGE_IMAGE else None
            ),
            small_image=self.SMALL_IMAGE or None,
            small_text=(
                self.SMALL_TEXT[:self.TEXT_LIMIT] if self.SMALL_IMAGE else None
            ),
        )

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
                rpc.loop.close()  # pyright: ignore[reportUnknownMemberType]
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
                except Exception as error:
                    logger.exception(f"Discord Presence update failed: {error}")
                    self._disconnect(rpc, clear=False)
                    rpc = None
                    self._wake.wait(self.RETRY_DELAY_SECONDS)
                    continue

                self._wake.wait()
        finally:
            if rpc is not None:
                self._disconnect(rpc)
                logger.debug("Discord Presence disconnected")
