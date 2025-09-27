from pathlib import Path
from ..utils import logger
from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError, TelegramUnauthorizedError
from aiogram.utils.token import TokenValidationError

ERRORS = {
    FileNotFoundError: ..., # file not created
    TelegramBadRequest: ..., # invalid chat id
    TelegramNetworkError: ..., # unstable internet
    **dict.fromkeys(
        [TelegramUnauthorizedError, TokenValidationError],
        ... # invalid bot token
    )
}

class TGBot:
    def __init__(self, token: str):
        self.bot = Bot(token=token)
    
    def close(self):
        if self.bot:
            self.bot.close()
        
    async def send(self, chat_id: int, *, message: str = None, path_to_file: str | Path = None, separate_sends: bool = True):
        try:
            if separate_sends:
                await self.send_message(chat_id, message=message)
                await self.send_file(chat_id, path_to_file=path_to_file)
            else:        
                await self.bot.send_document(
                    chat_id=chat_id,
                    text=message,
                    document=FSInputFile(path_to_file) if path_to_file else None,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
        except Exception as e:
            logger.exception(ERRORS.get(type(e), f'{...}: {e}')) # unknown error
        
    async def send_message(self, chat_id: int, *, message: str):
        await self.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
    async def send_file(self, chat_id: int, *, path_to_file: str | Path):
        await self.bot.send_document(
            chat_id=chat_id,
            document=FSInputFile(path_to_file),
        )