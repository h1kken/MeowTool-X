import asyncio
from httpx import AsyncClient
from src.utils.logger import logger
from src.exceptions.roblox import InvalidCookie, AccountBanned


class AsyncRequestManager:
    def __init__(self):
        self._client = AsyncClient()
    
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
        data: dict = None,
        json: dict = None,
        params: dict = None,
        headers: dict = None,
        cookies: dict = None,
        follow_redirects: bool = False
    ):
        while True:
            response = await self._client.request(
                method,
                url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                cookies=cookies,
                follow_redirects=follow_redirects
            )
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
        params: dict = None,
        headers: dict = None,
        cookies: dict = None,
        follow_redirects: bool = False
    ):
        return await self._request(
            'get',
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            follow_redirects=follow_redirects
        )
    
    async def post(
        self,
        url: str,
        *,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        headers: dict = None,
        cookies: dict = None
    ):
        return await self._request(
            'post',
            url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            cookies=cookies
        )