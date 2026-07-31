import typing as t
import collections.abc as cabc

import asyncio
import random

from aiohttp import (
    ClientError,
    ClientResponse,
    ClientSession,
    ClientTimeout,
    TCPConnector,
)

from src.exceptions.roblox import AccountBanned, InvalidCookie
from src.http.constants import (
    HTTP_CLIENT_CONNECTIONS_LIMIT,
    HTTP_CLIENT_MAX_RETRIES,
    HTTP_CLIENT_RETRY_BACKOFF,
    HTTP_CLIENT_RETRY_DELAY_SECONDS,
    HTTP_CLIENT_RETRY_MAX_DELAY_SECONDS,
    HTTP_CLIENT_TIMEOUT_SECONDS,
)
from src.utils.logging.decorators import log_network_request
from src.utils.logging import logger


class BaseHttpClient:
    def __init__(self, proxies: list[str] | None = None) -> None:
        self._session = ClientSession(
            connector=TCPConnector(limit=HTTP_CLIENT_CONNECTIONS_LIMIT)
        )
        self._proxies = proxies
    
    async def __aenter__(self) -> "BaseHttpClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
        
    async def close(self) -> None:
        await self._session.close()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        data: cabc.Mapping[str, object] | None = None,
        json: cabc.Mapping[str, object] | None = None,
        params: cabc.Mapping[str, str] | None = None,
        headers: cabc.Mapping[str, str] | None = None,
        cookies: cabc.Mapping[str, str] | None = None,
        allow_redirects: bool = False,
        timeout: ClientTimeout | None = None,
        ssl: bool = False,
    ) -> ClientResponse | None:
        if timeout is None:
            timeout = ClientTimeout(total=HTTP_CLIENT_TIMEOUT_SECONDS)

        last_error: BaseException | None = None
        for attempt in range(1, HTTP_CLIENT_MAX_RETRIES + 1):
            response: ClientResponse | None = None
            try:
                proxy = random.choice(self._proxies) if self._proxies else None
                response = await self._session.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json=json,
                    headers=headers,
                    cookies=cookies,
                    allow_redirects=allow_redirects,
                    proxy=proxy,
                    timeout=timeout,
                    ssl=ssl
                )
                return await self._handle_response(method, url, response)
            except (InvalidCookie, AccountBanned):
                raise
            except (ClientError, asyncio.TimeoutError, OSError, RuntimeError) as error:
                last_error = error
                status = response.status if response is not None else 'ERR'
                logger.exception(f'[{method.upper()}:{status}] URL: {url}')
                if attempt < HTTP_CLIENT_MAX_RETRIES:
                    delay = min(
                        HTTP_CLIENT_RETRY_MAX_DELAY_SECONDS,
                        HTTP_CLIENT_RETRY_DELAY_SECONDS * (HTTP_CLIENT_RETRY_BACKOFF ** (attempt - 1)),
                    )
                    await asyncio.sleep(delay)

        if last_error is not None:
            raise last_error
        raise RuntimeError(f'Failed request without specific error: {method.upper()} {url}')
                        
    async def _handle_response(
        self,
        method: str,
        url: str,
        response: ClientResponse,
    ) -> ClientResponse | None:
        raise NotImplementedError
        
    # @log_network_request()
    # async def options(self, url: str, **kwargs: Any):
    #     return await self._request('options', url, **kwargs)
        
    @log_network_request
    async def get(self, url: str, **kwargs: t.Any) -> ClientResponse | None:
        return await self._request('get', url, **kwargs)
    
    @log_network_request
    async def post(self, url: str, **kwargs: t.Any) -> ClientResponse | None:
        return await self._request('post', url, **kwargs)
    
    # @log_network_request()
    # async def head(self, url: str, **kwargs: Any):
    #     return await self._request('head', url, **kwargs)
    
    # @log_network_request()
    # async def put(self, url: str, **kwargs: Any):
    #     return await self._request('put', url, **kwargs)
    
    # @log_network_request()
    # async def patch(self, url: str, **kwargs: Any):
    #     return await self._request('patch', url, **kwargs)
    
    # @log_network_request()
    # async def delete(self, url: str, **kwargs: Any):
    #     return await self._request('delete', url, **kwargs)


