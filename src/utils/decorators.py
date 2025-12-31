import time
import functools
from pathlib import Path
from aiohttp import ClientResponse
from src.utils.logger import logger
from typing import Callable, Awaitable, Any


def log_action(action: str):
    def log_action_decorator(func):
        # @functools.wraps(func)
        def log_action_wrapper(path: Path, *args, **kwargs):
            try:
                return func(path, *args, **kwargs)
            except FileExistsError:
                logger.info(f'Can\'t {action} \'{path.name}\' that already exists')
            except Exception as e:
                logger.exception(f'Can\'t {action}: {path.name}. Error: {type(e).__name__}')
        return log_action_wrapper
    return log_action_decorator

def log_network_request(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        end = time.perf_counter()
        elapsed_ms = int((end - start) * 1000)
        if isinstance(result, ClientResponse):
            logger.debug(f'[{func.__name__.upper()}:{result.status}] {result.url} for {elapsed_ms}ms')
        return result
    return wrapper