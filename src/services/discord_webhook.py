from discord_webhook import DiscordWebhook, DiscordEmbed
from pathlib import Path
from requests.exceptions import InvalidURL, InvalidSchema, MissingSchema
from ..utils import logger

ERRORS = {
    FileNotFoundError: ..., # file not found
    ConnectionError: ..., # unstable internet
    **dict.fromkeys(
        [InvalidURL, InvalidSchema, MissingSchema],
        ... # invalid url
    )
}

RESPONSES = {
    **dict.fromkeys(
        [401, 404],
        ... # typo in webhook url
    ),
    413: ... # file is too big
}

class DSWebhook:
    def __init__(self, url: str):
        self.webhook = DiscordWebhook(
            url=url,
            rate_limit_retry=True
        )

    def add_embed(self, webhook: DiscordWebhook, text: str, *, color: str = '#fff', thumbnail: str = None):
        embed = DiscordEmbed(
            description=text,
            color=color
        )
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        webhook.add_embed(embed)
        
    def add_file(self, path_to_file: str | Path, filename: str):
        with open(path_to_file, 'rb') as file:
            self.webhook.add_file(file=file.read(), filename=filename)

    def send(self):
        try:
            response = self.webhook.execute()
            status = response.status_code

            if status == 200:
                logger.info(...) # good
            else:
                logger.warning(RESPONSES.get(status, f'{...}: {status}')) # unknown status
        except Exception as e:
            logger.exception(ERRORS.get(type(e), f'{...}: {e}')) # unknown error