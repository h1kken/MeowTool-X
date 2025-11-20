import asyncio
from aiohttp import TCPConnector, ClientSession, ClientTimeout, ClientResponse
from aiohttp_socks import ProxyConnector
from typing import Optional
from src.utils.logger import logger
from src.exceptions.roblox import InvalidCookie, AccountBanned


class RobloxSessionManager:
    def __init__(self):
        self._session = ClientSession()
    
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
        timeout: int | ClientTimeout = ClientTimeout(5)
    ):
        while True:
            try:
                response: ClientResponse = await self._session.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json=json,
                    headers=headers,
                    cookies=cookies,
                    allow_redirects=allow_redirects,
                    timeout=timeout
                )
                status = response.status
                match status:
                    case 200:
                        return response
                    case 204:
                        return None
                    case 302 if response.headers.get('Location') == '/not-approved':
                        raise AccountBanned
                    case 302 | 401:
                        raise InvalidCookie
                    case 403 if method == 'post':
                        return response
                    case 403:
                        raise AccountBanned
                    case _:
                        logger.debug(f'[{status}] URL: {url}')
                        await asyncio.sleep(5)
            except Exception:
                logger.exception(f'[{method.upper()}:{status}] URL: {url}')
            
    
    async def get(
        self,
        url: str,
        *,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        allow_redirects: bool = False,
        timeout: int | ClientTimeout = ClientTimeout(5)
    ):
        return await self._request(
            'get',
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            allow_redirects=allow_redirects,
            timeout=timeout
        )
    
    async def post(
        self,
        url: str,
        *,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        timeout: int | ClientTimeout = ClientTimeout(5)
    ):
        return await self._request(
            'post',
            url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            cookies=cookies,
            timeout=timeout
        )