WINDOW_X = 900
WINDOW_Y = 500

WINDOW_TITLEBAR_HEIGHT = 32
WINDOW_TITLEBAR_APP_ICON_SIZE = 18
WINDOW_TITLEBAR_BUTTON_WIDTH = 40
WINDOW_TITLEBAR_BUTTON_HEIGHT = 28
WINDOW_TITLEBAR_BUTTON_ICON_SIZE = 14

PRELOAD_WINDOW_WIDTH = 400
PRELOAD_WINDOW_HEIGHT = 500
PRELOAD_LAYOUT_MARGINS = 34
PRELOAD_TOP_SPACING = 8
PRELOAD_MIDDLE_SPACING = 12
PRELOAD_RING_SPACING = 8
PRELOAD_RING_MIN_SIZE = 220
PRELOAD_TITLE_FONT_SIZE = 23
PRELOAD_STATUS_FONT_SIZE = 13
PRELOAD_SUBTITLE_FONT_SIZE = 11
PRELOAD_COUNT_FONT_SIZE = 10
PRELOAD_RING_VALUE_FONT_SIZE = 16
PRELOAD_ENTRY_ANIMATION_MS = 220
PRELOAD_FLUSH_FPS = 60.0
PRELOAD_DRAG_FLUSH_FPS = 30.0
PRELOAD_DEFAULT_STAGE = 'Preparing startup counters'
PRELOAD_DEFAULT_STATUS = 'Booting up...'
PRELOAD_DEFAULT_SUBTITLE = ''
PRELOAD_DEFAULT_COUNTER = '0 / 0'
PRELOAD_BRAND_MIN_WIDTH = 120
PRELOAD_BRAND_TARGET_MIN_WIDTH = 140
PRELOAD_BRAND_WIDTH_RATIO = 0.76
PRELOAD_BRAND_MIN_HEIGHT = 40
PRELOAD_BRAND_HEIGHT_RATIO = 0.12

PRELOAD_STAGE_TEXT_MAP = {
    'Preparing startup counters': 'Preparing startup assets...',
    'Configuring main window': 'Building the main window shell...',
    'Building interface shell': 'Assembling interface assets...',
    'Starting animation engine': 'Loading animation assets...',
    'Starting theme engine': 'Compiling theme assets...',
    'Applying current theme': 'Applying the current visual pack...',
    'Prewarming Settings: Config and Theme': 'Caching settings assets for Config and Theme...',
    'Finalizing startup': 'Final polish before launch...',
}
THEME_AUTO_SAVE_DEBOUNCE_MS = 180

SIDEBAR_MEDIA_HEIGHT = 96
SIDEBAR_MEDIA_MARGIN = 8

SIDEBAR_MEDIA_GIF_EXTENSIONS = {
    '.gif',
}

SIDEBAR_MEDIA_IMAGE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.bmp',
    '.webp', '.svg', '.ico',
}

SIDEBAR_MEDIA_VIDEO_EXTENSIONS = {
    '.mp4', '.webm', '.avi',
    '.mov', '.mkv',
}


__all__ = [name for name in globals() if name.isupper()]
