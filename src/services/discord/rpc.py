from __future__ import annotations

import typing as t

import threading
from time import time

from pypresence.exceptions import DiscordError, DiscordNotFound, InvalidPipe, PipeClosed
from pypresence.presence import Presence
from pypresence.types import ActivityType

from src.app.constants import PROGRAM_NAME
from src.config.enums import ConfigKey as CKey
from src.utils.logging import logger

if t.TYPE_CHECKING:
    from src.ui.windows import MainWindow
    from src.config import Config


class DiscordRPC:
    APP_ID = '1493918950344626216'
    
    RETRY_DELAY_SECONDS = 5.0

    ACTIVITY_TYPE = ActivityType.PLAYING
    NAME = PROGRAM_NAME
    # LARGE_IMAGE = None
    # LARGE_TEXT = None
    # SMALL_IMAGE = None
    # SMALL_TEXT = None

    def __init__(self, window: MainWindow, config: Config) -> None:
        self._window = window
        self._config = config
        
        self._started_at = int(time())
        
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None

        self._enabled = self._read_enabled()

        self._connect_signals()

    def _connect_signals(self) -> None:
        self._config.configLoaded.connect(self._on_config_loaded)
        self._config.valueChanged.connect(self._on_config_value_changed)
        self._window.pageChanged.connect(self._wake.set)

    def start(self) -> None:
        with self._lock:
            if self._worker is not None and self._worker.is_alive():
                return

            self._started_at = int(time())
            self._stop.clear()
            self._wake.clear()
            
            self._worker = threading.Thread(
                target=self._run,
                name='DiscordRPC',
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
        return bool(self._config.get(CKey.MISC_DISCORD_RPC))

    def _on_config_loaded(self) -> None:
        self._set_enabled(self._read_enabled())

    def _on_config_value_changed(self, key: str, _value: object) -> None:
        if key == CKey.MISC_DISCORD_RPC:
            self._on_config_loaded()

    def _set_enabled(self, enabled: bool) -> None:
        with self._lock:
            if enabled == self._enabled:
                return

            self._enabled = enabled
            if enabled:
                self._started_at = int(time())

        self._wake.set()

    def _connect(self) -> Presence | None:
        for pipe in range(10):
            rpc: Presence | None = None
            try:
                rpc = Presence(self.APP_ID, pipe=pipe)
                rpc.connect()
                logger.info(f'Discord Presence connected (pipe {pipe})')
                return rpc
            except (DiscordNotFound, InvalidPipe, PipeClosed, OSError):
                self._disconnect(rpc, clear=False)
            except DiscordError as e:
                self._disconnect(rpc, clear=False)
                logger.warning(f'Discord Presence connection failed: {e}')
                return None
            except Exception as e:
                self._disconnect(rpc, clear=False)
                logger.exception(f'Discord Presence connection failed: {e}')
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

                if not self._enabled:
                    if rpc is not None:
                        self._disconnect(rpc)
                        rpc = None
                        logger.info('Discord Presence disconnected')
                    self._wake.wait()
                    continue

                if rpc is None:
                    rpc = self._connect()
                    if rpc is None:
                        self._wake.wait(self.RETRY_DELAY_SECONDS)
                    continue

                try:
                    self._update(rpc)
                except (DiscordNotFound, InvalidPipe, PipeClosed, BrokenPipeError, OSError):
                    self._disconnect(rpc, clear=False)
                    rpc = None
                    self._wake.wait(self.RETRY_DELAY_SECONDS)
                    continue
                except Exception as e:
                    logger.exception(f'Discord Presence update failed: {e}')
                    self._disconnect(rpc, clear=False)
                    rpc = None
                    self._wake.wait(self.RETRY_DELAY_SECONDS)
                    continue

                self._wake.wait()
        finally:
            if rpc is not None:
                self._disconnect(rpc)
                logger.debug('Discord Presence disconnected')

    def _update(self, rpc: Presence) -> None:
        rpc.update( # pyright: ignore[reportUnknownMemberType]
            start=max(1, self._started_at),
            
            activity_type=self.ACTIVITY_TYPE,
            name=self.NAME,
            details=' > '.join(self._window.page_state()),
            
            # large_image=self.LARGE_IMAGE,
            # large_text=self.LARGE_TEXT,
            # small_image=self.SMALL_IMAGE,
            # small_text=self.SMALL_TEXT,
        )
