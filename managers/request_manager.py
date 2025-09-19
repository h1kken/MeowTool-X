import time
import httpx
from utils.logger import logger
from exceptions.roblox_exceptions import (
    InvalidCookie,
    AccountBanned
)


class RequestManager:
    def __init__(self, *, headers: dict=None, cookies: dict=None):
        self.headers = headers
        self.cookies = cookies
    
    def __enter__(self):
        self._client = httpx.Client(headers=self.headers, cookies=self.cookies)
        return self
    
    def __exit__(self, *_):
        self._client.close()
        self._client = None
        return False
    
    def get(self, url: str):
        for i in range(1, 10):
            response = self._client.get(url)
            match response.status_code:
                case 200:
                    return response
                case 204:
                    return None
                case 302 | 401:
                    raise InvalidCookie
                case 403:
                    raise AccountBanned
                case _:
                    logger.debug(f'[{response.status_code}] URL: {url} | Try #{i}')
                    time.sleep(10)
    
    def post(self, url: str, *, data: dict=None):
        for i in range(1, 10):
            response = self._client.post(url, data=data)
            match response.status_code:
                case 200 | 403:
                    return response
                case 401:
                    raise InvalidCookie
                case _:
                    logger.debug(f'[{response.status_code}] URL: {url} | Try #{i}')
                    time.sleep(10)