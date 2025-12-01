import random
import asyncio
from aiohttp import TCPConnector, ClientSession, ClientTimeout, ClientResponse
from typing import Any, Optional
from src.utils.logger import logger
from src.exceptions.roblox import InvalidCookie, AccountBanned
from src.utils.consts import HTTP_CLIENT_MAX_RETRIES


class BaseHttpClient:
    def __init__(self, proxies: Optional[list[str]] = None):
        self._session = ClientSession(TCPConnector(limit=0, ssl=False))
        self._proxies = proxies
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()
        
    async def close(self):
        await self._session.close()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        allow_redirects: bool = False,
        timeout: ClientTimeout = ClientTimeout(5)
    ):
        i = 0
        while i < HTTP_CLIENT_MAX_RETRIES:
            try:
                proxy = random.choice(self._proxies) if self._proxies else None
                response: ClientResponse = await self._session.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json=json,
                    headers=headers,
                    cookies=cookies,
                    allow_redirects=allow_redirects,
                    proxy=proxy,
                    timeout=timeout
                )
                return await self._handle_response(method, url, response)
            except (InvalidCookie, AccountBanned):
                raise
            except Exception:
                i += 1
                status = getattr(response, 'status', 'ERR')
                logger.exception(f'[{method.upper()}:{status}] URL: {url}')
                await asyncio.sleep(5)
                        
    async def _handle_response(self, method: str, url: str, response: ClientResponse) -> Optional[ClientResponse]:
        ...
                        
    async def get(self, url: str, **kwargs: Any):
        return await self._request('get', url, **kwargs)
    
    async def post(self, url: str, **kwargs: Any):
        return await self._request('post', url, **kwargs)
    
    async def head(self, url: str, **kwargs: Any):
        return await self._request('head', url, **kwargs)