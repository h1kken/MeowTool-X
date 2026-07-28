import typing as t

from aiohttp import ClientResponse

from src.exceptions.roblox import AccountBanned, InvalidCookie
from src.http.base_client import BaseHttpClient
from src.utils.logging import logger


class RobloxHttpClient(BaseHttpClient):
    def __init__(self, proxies: list[str] | None = None):
        super().__init__(proxies=proxies)
        
    async def _handle_response(self, method: str, url: str, response: ClientResponse) -> ClientResponse:
        # status = response.status if locals().get('response') else 'ERR'
        match response.status:
            case 200:
                return response
            case 403 if method == 'post':
                return response
            case 204:
                return response
            case 302 if response.headers.get('Location') == '/not-approved':
                raise AccountBanned
            case 302 | 401:
                raise InvalidCookie
            case 403:
                raise AccountBanned
            case _:
                logger.debug(f'[{method.upper()}:{response.status}] URL: {url}')
                raise RuntimeError(f'Unexpected HTTP status {response.status} for {method.upper()} {url}')

    async def get(self, url: str, **kwargs: t.Any) -> ClientResponse:
        response = await super().get(url, **kwargs)
        if response is None:
            raise RuntimeError(f'GET returned no response for {url}')
        return response

    async def post(self, url: str, **kwargs: t.Any) -> ClientResponse:
        response = await super().post(url, **kwargs)
        if response is None:
            raise RuntimeError(f'POST returned no response for {url}')
        return response
