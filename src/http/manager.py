import asyncio
from aiohttp import TCPConnector, ClientSession, ClientTimeout, ClientResponse, ClientOSError, ServerDisconnectedError
from aiohttp.http_exceptions import TransferEncodingError
from aiohttp.client_exceptions import ClientPayloadError, SocketTimeoutError
from aiohttp_socks import ProxyConnector, ProxyError
from typing import Optional
from src.utils.logger import logger
from src.exceptions.roblox import InvalidCookie, AccountBanned


class AsyncRequestManager:
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
        follow_redirects: bool = False
    ):
        while True:
            response: ClientResponse = await self._session.request(
                method,
                url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                cookies=cookies,
                follow_redirects=follow_redirects
            )
            status = response.status
            match status:
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
                    logger.debug(f'[{status}] URL: {url}')
                    await asyncio.sleep(10)
    
    async def get(
        self,
        url: str,
        *,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
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
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None
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