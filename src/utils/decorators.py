import functools
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from aiohttp import ClientResponse

from src.utils.logging import logger


def log_action(action: str, *, re_raise: bool = False):
    def log_action_decorator(func):
        @functools.wraps(func)
        def log_action_wrapper(path: Path, *args, **kwargs):
            with logger.origin_scope(overwrite=False, depth=2):
                try:
                    return func(path, *args, **kwargs)
                except FileExistsError:
                    logger.debug(f'Can\'t {action} \'{path}\' that already exists')
                    if re_raise:
                        raise
                except Exception as e:
                    logger.exception(f'Can\'t {action}: {path}. Error: {type(e).__name__}')
                    if re_raise:
                        raise
        return log_action_wrapper
    return log_action_decorator


def log_network_request(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        with logger.origin_scope(overwrite=False, depth=2):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            end = time.perf_counter()
            elapsed_ms = int((end - start) * 1000)
            if isinstance(result, ClientResponse):
                logger.debug(f'[{func.__name__.upper()}:{result.status}] {result.url} for {elapsed_ms}ms')
            return result
    return wrapper
