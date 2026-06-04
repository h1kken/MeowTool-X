import sys

VERSION = 'v1.0.0'
PROGRAM_NAME = 'MeowTool... Meow :3'

DISCORD_PRESENCE_APP_ID = '1493918950344626216'
DISCORD_PRESENCE_LARGE_IMAGE_KEY = ''
DISCORD_PRESENCE_LARGE_IMAGE_TEXT = 'MeowTool X'
DISCORD_PRESENCE_SMALL_IMAGE_KEY = ''
DISCORD_PRESENCE_SMALL_IMAGE_TEXT = ''

COUNT_UPPER_LINE = 140
COUNT_LOWER_LINE = 119
ASCII_MEOWTOOL = rf'''
{'‾' * COUNT_UPPER_LINE}
    __    __     ______     ______     __     __     ______    ______     ______     __            __  __
   ╱╲ "─.╱  ╲   ╱╲  ___╲   ╱╲  __ ╲   ╱╲ ╲  _ ╲ ╲   ╱╲__  _╲  ╱╲  __ ╲   ╱╲  __ ╲   ╱╲ ╲          ╱╲_╲_╲_╲
   ╲ ╲ ╲─.╱╲ ╲  ╲ ╲  __╲   ╲ ╲ ╲ ╲ ╲  ╲ ╲ ╲╱ ".╲ ╲  ╲╱_╱╲ ╲╱  ╲ ╲ ╲ ╲ ╲  ╲ ╲ ╲ ╲ ╲  ╲ ╲ ╲         ╲╱_╱╲_╲╱
    ╲ ╲ ╲ ╲ ╲ ╲  ╲ ╲    ‾╲  ╲ ╲ ‾‾  ╲  ╲ ╲ .╱".~╲ ╲    ╲ ╲ ╲   ╲ ╲ ‾‾  ╲  ╲ ╲ ‾‾  ╲  ╲ ╲ ‾‾‾‾╲      ╱╲‾╲╱╲‾╲
     ╲╱‾╱  ╲╱‾╱   ╲╱‾‾‾‾‾╱   ╲╱‾‾‾‾‾╱   ╲╱‾╱   ╲╱‾╱     ╲╱‾╱    ╲╱‾‾‾‾‾╱   ╲╱‾‾‾‾‾╱   ╲╱‾‾‾‾‾╱      ╲╱‾╱╲╱‾╱
      ‾‾    ‾‾     ‾‾‾‾‾‾     ‾‾‾‾‾‾     ‾‾     ‾‾       ‾‾      ‾‾‾‾‾‾     ‾‾‾‾‾‾     ‾‾‾‾‾‾        ‾‾  ‾‾
{'_' * COUNT_LOWER_LINE}
'''.strip()


def _is_console_stream(stream: object) -> bool:
    isatty = getattr(stream, 'isatty', None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except Exception:
        return False


IS_LAUNCHED_WITH_CONSOLE = _is_console_stream(sys.stdout)


__all__ = [name for name in globals() if name.isupper()]
