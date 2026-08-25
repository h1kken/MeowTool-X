import typing as t
import collections.abc as cabc

import functools
import time
from pathlib import Path

from aiohttp import ClientResponse

from src.utils.logging import logger

P = t.ParamSpec('P')
R = t.TypeVar('R')
T = t.TypeVar('T')


@t.overload
def log_action(action: str, *, re_raise: t.Literal[True]) -> cabc.Callable[[cabc.Callable[t.Concatenate[Path, P], R]], cabc.Callable[t.Concatenate[Path, P], R]]: ...

@t.overload
def log_action(action: str, *, re_raise: t.Literal[False] = False) -> cabc.Callable[[cabc.Callable[t.Concatenate[Path, P], R]], cabc.Callable[t.Concatenate[Path, P], R | None]]: ...

def log_action(action: str, *, re_raise: bool = False) -> cabc.Callable[[cabc.Callable[t.Concatenate[Path, P], R]], cabc.Callable[t.Concatenate[Path, P], R] | cabc.Callable[t.Concatenate[Path, P], R | None]]:
    def log_action_decorator(func: cabc.Callable[t.Concatenate[Path, P], R]) -> cabc.Callable[t.Concatenate[Path, P], R] | cabc.Callable[t.Concatenate[Path, P], R | None]:
        if re_raise:
            @functools.wraps(func)
            def log_action_wrapper_reraise(path: Path, *args: P.args, **kwargs: P.kwargs) -> R:
                with logger.origin_scope(depth=2):
                    try:
                        return func(path, *args, **kwargs)
                    except FileExistsError:
                        logger.debug(f'Can\'t {action}: {path}: File already exists')
                        raise
                    except Exception as e:
                        logger.exception(f'Can\'t {action}: {path}: {type(e).__name__}')
                        raise

            return log_action_wrapper_reraise

        @functools.wraps(func)
        def log_action_wrapper(path: Path, *args: P.args, **kwargs: P.kwargs) -> R | None:
            with logger.origin_scope(depth=2):
                try:
                    return func(path, *args, **kwargs)
                except FileExistsError as e:
                    logger.debug(f'Can\'t {action}: {path}: File already exists')
                    if re_raise:
                        raise
                except Exception as e:
                    logger.exception(f'Can\'t {action}: {path}: {type(e).__name__}')
                    if re_raise:
                        raise
        return log_action_wrapper
    return log_action_decorator


def log_network_request(func: cabc.Callable[P, cabc.Awaitable[T]]) -> cabc.Callable[P, cabc.Awaitable[T]]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with logger.origin_scope(depth=2):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            end = time.perf_counter()
            elapsed_ms = int((end - start) * 1000)
            if isinstance(result, ClientResponse):
                logger.debug(f'[{func.__name__.upper()}:{result.status}] {result.url} for {elapsed_ms}ms')
            return result
    return wrapper
