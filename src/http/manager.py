import httpx
import atexit
import asyncio
from src.utils.logger import logger
from src.exceptions.roblox import (
    InvalidCookie,
    AccountBanned
)


class AsyncRequestManager:
    def __init__(self):
        self._client = httpx.AsyncClient()
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()
        
    async def close(self):
        await self._client.aclose()
    
    def update_headers(self, headers: dict):
        self._client.headers.update(headers)
    
    def update_cookies(self, cookies: dict):
        self._client.cookies.update(cookies)
    
    async def _request(
        self,
        method: str,
        url: str,
        *,
        cookies: dict = None,
        headers: dict = None,
        data: dict = None,
        json: dict = None,
        params: dict = None
    ):
        while True:
            response = await self._client.request(method, url, cookies=cookies, headers=headers, data=data, json=json, params=params)
            match response.status_code:
                case 200:
                    return response
                case 403 if method == 'post':
                    return response
                case 204:
                    return None
                case 302 | 401:
                    raise InvalidCookie
                case 403:
                    raise AccountBanned
                case _:
                    logger.debug(f'[{response.status_code}] URL: {url}')
                    await asyncio.sleep(10)
    
    async def get(
        self,
        url: str,
        *,
        cookies: dict = None,
        headers: dict = None,
        params: dict = None
    ):
        return await self._request('get', url, cookies=cookies, headers=headers, params=params)
    
    async def post(
        self,
        url: str,
        *,
        cookies: dict = None,
        headers: dict = None,
        data: dict = None,
        json: dict = None,
        params: dict = None
    ):
        return await self._request('post', url, cookies=cookies, headers=headers, data=data, json=json, params=params)