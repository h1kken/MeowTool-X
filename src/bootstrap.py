from __future__ import annotations

from typing import Callable

from src.config.loader import config_loader
from src.config.manager import config
from src.theme.storage.loader import load_preload_theme
from src.ui.windows.main_window import MainWindow
from src.ui.windows.preload_screen import PreloadScreen
from src.utils.constants import (
    DEFAULT_THEME,
    IS_LAUNCHED_WITH_CONSOLE,
    PROGRAM_NAME,
    THEME_RUNTIME_RAINBOW_DURATION_FALLBACK,
    THEME_RUNTIME_RAINBOW_ENABLED_FALLBACK,
    THEME_RUNTIME_RAINBOW_PALETTE_FALLBACK,
)
from src.utils.debug import dump_object_tree
from src.utils.preload import format_preload_counter_with_label


def _startup_object_tree_enabled() -> bool:
    return IS_LAUNCHED_WITH_CONSOLE and bool(
        config_loader.get("Loader>Developer Mode", default=False)
    )


class _StartupProgressTracker:
    def __init__(
        self,
        callback: Callable[..., None] | None,
        stages: list[tuple[str, float]],
    ) -> None:
        self._callback = callback
        self._weights: dict[str, float] = {}
        self._offsets: dict[str, float] = {}
        self._last_value = 0.0

        total = 0.0
        for key, weight in stages:
            normalized = max(0.0, float(weight))
            self._offsets[key] = total
            self._weights[key] = normalized
            total += normalized

        self.total = max(1.0, total)

    def update(
        self,
        key: str,
        progress: float,
        stage: str,
        counter_text: str | None = None,
    ) -> None:
        if not callable(self._callback):
            return

        weight = self._weights.get(key, 0.0)
        offset = self._offsets.get(key, 0.0)
        clamped = max(0.0, min(1.0, float(progress)))
        current = offset + (weight * clamped)
        current = max(self._last_value, min(self.total, current))
        self._last_value = current
        self._callback(current, self.total, stage, counter_text)

    def complete(self, key: str, stage: str, counter_text: str | None = None) -> None:
        self.update(key, 1.0, stage, counter_text)


class AppBootstrap:
    def __init__(self, *, window_class: type[MainWindow] = MainWindow) -> None:
        self._window_class = window_class

    def run(self) -> MainWindow:
        theme_name = self._theme_name_on_load()
        preload = self._build_preload(theme_name)
        tracker = _StartupProgressTracker(preload.update_progress, self._stage_weights())

        preload.prepare_startup(
            total=tracker.total,
            stage="Preparing startup counters",
            counter_text=format_preload_counter_with_label(
                0,
                tracker.total,
                "PRELOAD_COUNTER_LABEL_STARTUP",
            ),
        )
        preload.update_progress(
            0,
            tracker.total,
            f"Bootstrapping {PROGRAM_NAME}",
            counter_text=format_preload_counter_with_label(
                0,
                tracker.total,
                "PRELOAD_COUNTER_LABEL_STARTUP",
            ),
        )

        tracker.update(
            "window_shell",
            0.0,
            "Building main window shell",
            counter_text=format_preload_counter_with_label(
                0,
                tracker.total,
                "PRELOAD_COUNTER_LABEL_STARTUP",
            ),
        )
        window = self._window_class()
        tracker.complete(
            "window_shell",
            "Building main window shell",
            counter_text=format_preload_counter_with_label(
                1,
                tracker.total,
                "PRELOAD_COUNTER_LABEL_STARTUP",
            ),
        )

        tracker.update("pages", 0.0, "Loading application pages")
        window.build_pages(progress_callback=self._page_progress_callback(tracker))

        if _startup_object_tree_enabled():
            tracker.update("object_tree", 0.0, "Dumping object tree")
            dump_object_tree(
                window,
                progress_callback=self._object_tree_progress_callback(tracker),
            )
            tracker.complete("object_tree", "Dumping object tree")

        tracker.update("animation_engine", 0.0, "Starting animation engine")
        window.initialize_runtime_controllers()
        tracker.complete("animation_engine", "Starting animation engine")

        tracker.update("theme_engine", 0.0, "Starting theme engine")
        window.initialize_theme_manager()
        tracker.complete("theme_engine", "Starting theme engine")

        tracker.update("apply_theme", 0.0, "Applying current theme")
        window.apply_startup_theme(theme_name)
        window.reapply_runtime_theme_preferences()
        tracker.complete("apply_theme", "Applying current theme")

        tracker.update("settings_prewarm", 0.0, "Prewarming settings")
        window.preload_settings_pages(
            progress_callback=self._settings_prewarm_progress_callback(tracker)
        )

        tracker.update("services", 0.0, "Starting runtime services")
        window.start_discord_presence()
        window.resume_theme_events()
        tracker.complete("services", "Starting runtime services")

        preload.update_progress(
            tracker.total,
            tracker.total,
            "Startup complete",
        )
        window.show()
        preload.close()
        return window

    def _build_preload(self, theme_name: str) -> PreloadScreen:
        preload = PreloadScreen(theme=load_preload_theme(theme_name))
        enabled, duration, palette = self._runtime_theme_preferences()
        preload.apply_runtime_theme_preferences(enabled, duration, palette)
        return preload

    def _theme_name_on_load(self) -> str:
        configured = str(config.get("General>Theme", default=DEFAULT_THEME.stem)).strip()
        return configured or DEFAULT_THEME.stem

    def _runtime_theme_preferences(self) -> tuple[bool, int, str]:
        enabled = bool(
            config.get(
                "Misc>Rainbow Mode>Enabled",
                default=THEME_RUNTIME_RAINBOW_ENABLED_FALLBACK,
            )
        )
        try:
            duration = max(
                1000,
                int(
                    config.get(
                        "Misc>Rainbow Mode>Cycle Duration",
                        default=THEME_RUNTIME_RAINBOW_DURATION_FALLBACK,
                    )
                ),
            )
        except (TypeError, ValueError):
            duration = THEME_RUNTIME_RAINBOW_DURATION_FALLBACK

        palette = (
            str(
                config.get(
                    "Misc>Rainbow Mode>Palette",
                    default=THEME_RUNTIME_RAINBOW_PALETTE_FALLBACK,
                )
            ).strip()
            or THEME_RUNTIME_RAINBOW_PALETTE_FALLBACK
        )
        return enabled, duration, palette

    def _stage_weights(self) -> list[tuple[str, float]]:
        return [
            ("window_shell", 1.0),
            ("pages", float(self._window_class.startup_page_total())),
            ("object_tree", 1.0 if _startup_object_tree_enabled() else 0.0),
            ("animation_engine", 1.0),
            ("theme_engine", 1.0),
            ("apply_theme", 1.0),
            (
                "settings_prewarm",
                float(self._window_class.startup_settings_prewarm_total()),
            ),
            ("services", 1.0),
        ]

    def _page_progress_callback(
        self,
        tracker: _StartupProgressTracker,
    ) -> Callable[[int, int, str], None]:
        def callback(current: int, total: int, stage: str) -> None:
            safe_total = max(1, int(total))
            tracker.update(
                "pages",
                float(current) / float(safe_total),
                stage,
                counter_text=format_preload_counter_with_label(
                    current,
                    safe_total,
                    "PRELOAD_COUNTER_LABEL_PAGES",
                ),
            )

        return callback

    def _settings_prewarm_progress_callback(
        self,
        tracker: _StartupProgressTracker,
    ) -> Callable[[int, int, str], None]:
        def callback(current: int, total: int, stage: str) -> None:
            safe_total = max(1, int(total))
            tracker.update(
                "settings_prewarm",
                float(current) / float(safe_total),
                stage,
                counter_text=format_preload_counter_with_label(
                    current,
                    safe_total,
                    "PRELOAD_COUNTER_LABEL_SETTINGS_WARMUP",
                ),
            )

        return callback

    def _object_tree_progress_callback(
        self,
        tracker: _StartupProgressTracker,
    ) -> Callable[[int, int, object], None]:
        def callback(visited: int, total: int, obj: object) -> None:
            safe_total = max(1, int(total))
            obj_name = ""
            if hasattr(obj, "objectName"):
                try:
                    obj_name = str(obj.objectName()).strip()
                except Exception:
                    obj_name = ""
            target = obj_name or obj.__class__.__name__
            tracker.update(
                "object_tree",
                float(visited) / float(safe_total),
                f"Dumping object tree: {visited}/{safe_total} · {target}",
                counter_text=format_preload_counter_with_label(
                    visited,
                    safe_total,
                    "PRELOAD_COUNTER_LABEL_OBJECT_TREE",
                ),
            )

        return callback
