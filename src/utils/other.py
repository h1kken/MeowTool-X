import os
import sys
from typing import Generator, TypeVar


def cls() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')
    
def beep() -> None:
    sys.stdout.write('\a')
    sys.stdout.flush()

T = TypeVar('T')

def chunked(seq: list[T], size: int) -> Generator[list[T], None, None]:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]
