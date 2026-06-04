from __future__ import annotations

import os
import threading
from time import time
from typing import Any

from PySide6.QtCore import QObject

from src.config.manager import config
from src.utils.constants import (
    DISCORD_PRESENCE_APP_ID,
    DISCORD_PRESENCE_LARGE_IMAGE_KEY,
    DISCORD_PRESENCE_SMALL_IMAGE_KEY,
    DISCORD_PRESENCE_SMALL_IMAGE_TEXT,
)
from src.utils.logging import logger

try:
    from pypresence import Presence
    from pypresence.exceptions import DiscordError, DiscordNotFound, InvalidPipe, PipeClosed
    from pypresence.types import ActivityType
except Exception:  # pragma: no cover - optional dependency safety
    Presence = None
    DiscordError = DiscordNotFound = InvalidPipe = PipeClosed = Exception
    ActivityType = None


class DiscordPresenceManager(QObject):
    DEFAULT_PAGE = 'Startup'
    RETRY_INTERVAL_SECONDS = 2.0
    CAPACITY_RETRY_SECONDS = 15.0

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._client_id = str(DISCORD_PRESENCE_APP_ID).strip()
        self._started_at = int(time())
        self._enabled = False
        self._page = self.DEFAULT_PAGE
        self._theme = ''
        self._details_override: str | None = None
        self._state_override: str | None = None
        self._preferred_pipe = 0
        self._force_republish_requested = False
        self._reconnect_requested = False
        self._capacity_warning_logged = False

        self._state_lock = threading.Lock()
        self._wake_event = threading.Event()
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

        config.config_loaded.connect(self._sync_enabled_state)
        config.value_changed.connect(self._on_config_value_changed)

    def start(self) -> None:
        self._started_at = int(time())
        self._ensure_worker_started()
        self._sync_enabled_state()

    def shutdown(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=3.0)
        self._worker_thread = None

    def set_page(self, page: str) -> None:
        normalized = self._normalize_page(page)
        with self._state_lock:
            if normalized == self._page:
                return
            self._page = normalized
        self._request_refresh()

    def set_theme(self, theme_name: str) -> None:
        normalized = str(theme_name).strip()
        with self._state_lock:
            if normalized == self._theme:
                return
            self._theme = normalized
        self._request_refresh()

    def set_activity(self, *, details: str | None = None, state: str | None = None) -> None:
        changed = False
        with self._state_lock:
            if details is not None:
                next_details = str(details).strip() or None
                if next_details != self._details_override:
                    self._details_override = next_details
                    changed = True
            if state is not None:
                next_state = str(state).strip() or None
                if next_state != self._state_override:
                    self._state_override = next_state
                    changed = True
        if changed:
            self._request_refresh()

    def clear_activity_override(self) -> None:
        with self._state_lock:
            if self._details_override is None and self._state_override is None:
                return
            self._details_override = None
            self._state_override = None
        self._request_refresh()

    def _ensure_worker_started(self) -> None:
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return

        self._stop_event.clear()
        self._wake_event.clear()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name='DiscordPresenceWorker',
            daemon=True,
        )
        self._worker_thread.start()

    def force_republish(self, *, reconnect: bool = False) -> None:
        self._request_refresh(force=True, reconnect=reconnect)

    def _request_refresh(self, *, force: bool = False, reconnect: bool = False) -> None:
        with self._state_lock:
            if force:
                self._force_republish_requested = True
            if reconnect:
                self._reconnect_requested = True
        self._wake_event.set()

    def _on_config_value_changed(self, key: str, _value: Any) -> None:
        if str(key).strip() == 'Outputs>Discord Presence>Enable Presence':
            self._sync_enabled_state()

    def _sync_enabled_state(self, *_args) -> None:
        enabled = bool(config.get('Outputs>Discord Presence>Enable Presence', default=False))
        with self._state_lock:
            was_enabled = bool(self._enabled)
            self._enabled = enabled
            if enabled and not was_enabled:
                self._started_at = int(time())
                self._force_republish_requested = True
                self._reconnect_requested = True
        self._request_refresh()

    def _snapshot_state(self) -> dict[str, Any]:
        with self._state_lock:
            state = {
                'enabled': bool(self._enabled),
                'client_id': self._client_id,
                'started_at': int(self._started_at),
                'page': self._page,
                'details_override': self._details_override,
                'state_override': self._state_override,
                'force_republish': bool(self._force_republish_requested),
                'reconnect': bool(self._reconnect_requested),
            }
            self._force_republish_requested = False
            self._reconnect_requested = False
            return state

    def _normalize_page(self, value: str) -> str:
        return str(value).strip() or self.DEFAULT_PAGE

    def _presence_details(self, state: dict[str, Any]) -> str:
        override = state.get('details_override')
        if isinstance(override, str) and override.strip():
            return override.strip()
        return self._normalize_page(str(state.get('page', self.DEFAULT_PAGE)))

    def _presence_state(self, state: dict[str, Any]) -> str:
        override = state.get('state_override')
        if isinstance(override, str) and override.strip():
            return override.strip()
        return ''

    def _build_presence_payload(self, state: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'pid': os.getpid(),
            'start': max(1, int(state.get('started_at', int(time())))),
        }

        details = self._presence_details(state)[:128]
        if details:
            payload['details'] = details

        if ActivityType is not None:
            payload['activity_type'] = ActivityType.PLAYING

        status = self._presence_state(state)[:128]
        if status:
            payload['state'] = status

        large_image = str(DISCORD_PRESENCE_LARGE_IMAGE_KEY).strip()
        if large_image:
            payload['large_image'] = large_image

        small_image = str(DISCORD_PRESENCE_SMALL_IMAGE_KEY).strip()
        if small_image:
            payload['small_image'] = small_image
            small_text = str(DISCORD_PRESENCE_SMALL_IMAGE_TEXT or '').strip()
            if small_text:
                payload['small_text'] = small_text[:128]

        return payload

    @staticmethod
    def _payload_signature(payload: dict[str, Any]) -> tuple[tuple[str, str], ...]:
        return tuple((str(key), repr(payload[key])) for key in sorted(payload))

    def _disconnect_rpc(self, rpc) -> None:
        if rpc is None:
            return
        try:
            rpc.clear(pid=os.getpid())
        except Exception:
            pass
        try:
            rpc.close()
        except Exception:
            pass

    def _cleanup_failed_rpc(self, rpc) -> None:
        if rpc is None:
            return
        try:
            rpc.close()
        except Exception:
            pass
        loop = getattr(rpc, 'loop', None)
        if loop is not None:
            try:
                if not loop.is_closed():
                    loop.close()
            except Exception:
                pass

    def _connect_rpc(self, client_id: str, *, missing_library_logged: bool, missing_app_id_logged: bool):
        if not client_id:
            if not missing_app_id_logged:
                logger.warning('Discord Presence is enabled, but DISCORD_PRESENCE_APP_ID is empty.')
            return None, missing_library_logged, True, self.RETRY_INTERVAL_SECONDS

        if Presence is None:
            if not missing_library_logged:
                logger.warning('Discord Presence is enabled, but pypresence is not installed.')
            return None, True, missing_app_id_logged, self.RETRY_INTERVAL_SECONDS

        pipe_order = [self._preferred_pipe, *[pipe for pipe in range(10) if pipe != self._preferred_pipe]]
        last_pipe_error: Exception | None = None
        for pipe in pipe_order:
            rpc = None
            try:
                rpc = Presence(client_id, pipe=pipe)
                rpc.connect()
                self._preferred_pipe = pipe
                self._capacity_warning_logged = False
                logger.info(f'Discord Presence connected (pipe {pipe})')
                return rpc, False, False, self.RETRY_INTERVAL_SECONDS
            except DiscordError as e:
                self._cleanup_failed_rpc(rpc)
                if getattr(e, 'code', None) == 1006 or 'Server at capacity' in str(e):
                    if not self._capacity_warning_logged:
                        logger.warning('Discord Presence temporarily unavailable: Discord server at capacity.')
                        self._capacity_warning_logged = True
                    return None, False, False, self.CAPACITY_RETRY_SECONDS
                logger.debug(f'Discord Presence connect skipped on pipe {pipe}: {type(e).__name__}: {e}')
                last_pipe_error = e
                continue
            except (DiscordNotFound, InvalidPipe, OSError) as e:
                self._cleanup_failed_rpc(rpc)
                last_pipe_error = e
                continue
            except Exception as e:  # pragma: no cover - defensive guard
                self._cleanup_failed_rpc(rpc)
                logger.exception(f'Discord Presence connection failed on pipe {pipe}. Error: {e}')
                return None, False, False, self.RETRY_INTERVAL_SECONDS

        if last_pipe_error is not None:
            logger.debug(f'Discord Presence connect skipped: {type(last_pipe_error).__name__}: {last_pipe_error}')
        return None, False, False, self.RETRY_INTERVAL_SECONDS

    def _publish_presence(self, rpc, payload: dict[str, Any]) -> bool:
        try:
            rpc.update(**payload)
            return True
        except (DiscordNotFound, InvalidPipe, PipeClosed, BrokenPipeError, OSError) as e:
            logger.debug(f'Discord Presence update skipped: {type(e).__name__}: {e}')
            return False
        except Exception as e:  # pragma: no cover - defensive guard
            logger.exception(f'Discord Presence update failed. Error: {e}')
            return False

    def _wait_for_refresh(self, timeout: float | None = None) -> bool:
        triggered = self._wake_event.wait(timeout)
        self._wake_event.clear()
        return triggered

    def _worker_loop(self) -> None:
        rpc = None
        last_signature: tuple[tuple[str, str], ...] | None = None
        missing_library_logged = False
        missing_app_id_logged = False
        retry_delay = self.RETRY_INTERVAL_SECONDS

        while not self._stop_event.is_set():
            state = self._snapshot_state()
            enabled = bool(state.get('enabled'))
            reconnect = bool(state.get('reconnect'))
            force_republish = bool(state.get('force_republish'))

            if not enabled:
                last_signature = None
                if rpc is not None:
                    self._disconnect_rpc(rpc)
                    rpc = None
                    logger.debug('Discord Presence disconnected')
                self._wait_for_refresh()
                continue

            if reconnect and rpc is not None:
                self._disconnect_rpc(rpc)
                rpc = None
                last_signature = None
                logger.debug('Discord Presence reconnect requested')

            if rpc is None:
                rpc, missing_library_logged, missing_app_id_logged, retry_delay = self._connect_rpc(
                    str(state.get('client_id', '')).strip(),
                    missing_library_logged=missing_library_logged,
                    missing_app_id_logged=missing_app_id_logged,
                )
                if rpc is None:
                    self._wait_for_refresh(retry_delay)
                    continue
                last_signature = None
                retry_delay = self.RETRY_INTERVAL_SECONDS

            payload = self._build_presence_payload(state)
            signature = self._payload_signature(payload)
            if force_republish:
                last_signature = None
            if signature != last_signature:
                if self._publish_presence(rpc, payload):
                    last_signature = signature
                    self._wait_for_refresh()
                    continue

                self._disconnect_rpc(rpc)
                rpc = None
                last_signature = None
                self._wait_for_refresh(self.RETRY_INTERVAL_SECONDS)
                continue

            self._wait_for_refresh()

        if rpc is not None:
            self._disconnect_rpc(rpc)
            logger.debug('Discord Presence disconnected')
