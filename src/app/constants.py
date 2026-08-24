import sys


PROGRAM_TITLE = 'MeowTool... Meow :3'

PROGRAM_NAME = 'MeowTool X'
PROGRAM_VERSION = '1.0.0'

ASCII_MEOWTOOL = rf'''
{'‾' * 109}
    __    __     ______     ______     __     __     ______    ______     ______     __            __  __
   ╱╲ '─.╱  ╲   ╱╲  ___╲   ╱╲  __ ╲   ╱╲ ╲  _ ╲ ╲   ╱╲__  _╲  ╱╲  __ ╲   ╱╲  __ ╲   ╱╲ ╲          ╱╲_╲_╲_╲
   ╲ ╲ ╲─.╱╲ ╲  ╲ ╲  __╲   ╲ ╲ ╲ ╲ ╲  ╲ ╲ ╲╱ '.╲ ╲  ╲╱_╱╲ ╲╱  ╲ ╲ ╲ ╲ ╲  ╲ ╲ ╲ ╲ ╲  ╲ ╲ ╲         ╲╱_╱╲_╲╱
    ╲ ╲ ╲ ╲ ╲ ╲  ╲ ╲    ‾╲  ╲ ╲ ‾‾  ╲  ╲ ╲ .╱'. ╲ ╲    ╲ ╲ ╲   ╲ ╲ ‾‾  ╲  ╲ ╲ ‾‾  ╲  ╲ ╲ ‾‾‾‾╲      ╱╲‾╲╱╲‾╲
     ╲╱‾╱  ╲╱‾╱   ╲╱‾‾‾‾‾╱   ╲╱‾‾‾‾‾╱   ╲╱‾╱   ╲╱‾╱     ╲╱‾╱    ╲╱‾‾‾‾‾╱   ╲╱‾‾‾‾‾╱   ╲╱‾‾‾‾‾╱      ╲╱‾╱╲╱‾╱
      ‾‾    ‾‾     ‾‾‾‾‾‾     ‾‾‾‾‾‾     ‾‾     ‾‾       ‾‾      ‾‾‾‾‾‾     ‾‾‾‾‾‾     ‾‾‾‾‾‾        ‾‾  ‾‾
{'_' * 104}
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
