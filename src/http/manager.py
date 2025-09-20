import httpx
import atexit
import asyncio
from utils.logger import logger
from exceptions.roblox import (
    InvalidCookie,
    AccountBanned
)


class AsyncRequestManager:
    def __init__(self, *, headers: dict = None, cookies: dict = None):
        self._client = httpx.AsyncClient(headers=headers, cookies=cookies)
        atexit.register(self._cleanup)
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    def _cleanup(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.close())
        else:
            loop.create_task(self.close())
        
    async def close(self):
        await self._client.aclose()
    
    def set_headers(self, headers: dict):
        self._client.headers.update(headers)
    
    def set_cookies(self, cookies: dict):
        self._client.cookies.update(cookies)
    
    async def _request(self, method: str, url: str, *, data: dict = None, json: dict = None, params: dict = None):
        while True:
            response = await self._client.request(method, url, data=data, json=json, params=params)
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
    
    async def get(self, url: str, *, params: dict = None):
        return await self._request('get', url, params=params)
    
    async def post(self, url: str, *, data: dict = None, json: dict = None, params: dict = None):
        return await self._request('post', url, data=data, json=json, params=params)
    
    
client = AsyncRequestManager()