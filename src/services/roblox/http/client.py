import asyncio
from typing import Optional
from aiohttp import ClientResponse
from src.utils.logger import logger
from src.http_client.base import BaseHttpClient
from src.exceptions.roblox import InvalidCookie, AccountBanned


class RobloxHttpClient(BaseHttpClient):
    def __init__(self, proxies: Optional[list[str]] = None):
        super().__init__(proxies=proxies)
        
    async def _handle_response(self, method: str, url: str, response: ClientResponse) -> Optional[ClientResponse]:
        # status = response.status if locals().get('response') else 'ERR'
        match response.status:
            case 200:
                return response
            case 403 if method == 'post':
                return response
            case 204:
                return None
            case 302 if response.headers.get('Location') == '/not-approved':
                raise AccountBanned
            case 302 | 401:
                raise InvalidCookie
            case 403:
                raise AccountBanned
            case _:
                logger.debug(f'[{method.upper()}:{response.status}] URL: {url}')
                await asyncio.sleep(5)
