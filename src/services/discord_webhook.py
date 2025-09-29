from discord_webhook import DiscordWebhook, DiscordEmbed
from pathlib import Path
from requests.exceptions import InvalidURL, InvalidSchema, MissingSchema
from ..utils import logger
from ..translation import translator as t

ERRORS = {
    FileNotFoundError: t.tr('ERR_FL_N_FND'),
    ConnectionError: t.tr('ERR_UNSTBL_INT_CONN'),
    **dict.fromkeys(
        [InvalidURL, InvalidSchema, MissingSchema],
        t.tr('ERR_INV_URL')
    )
}

RESPONSES = {
    **dict.fromkeys(
        [401, 404],
        t.tr('ERR_TP_IN_WBHK_URL')
    ),
    413: t.tr('ERR_FL_T_BIG')
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
                logger.info(t.tr('GOOD'))
            else:
                logger.warning(RESPONSES.get(status, f'{t.tr('ERR_STTS')}: {status}'))
        except Exception as e:
            logger.exception(ERRORS.get(type(e), f'{t.tr('ERR_UNK')}: {e}'))