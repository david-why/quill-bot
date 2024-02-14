import logging
import os

from interactions import Client, listen, logger_name

from database import Database


class CustomClient(Client):
    logger = logging.getLogger(logger_name)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.database = Database()

    @listen()
    async def on_startup(self):
        self.logger.info(f'{os.getenv("PROJECT_NAME")} - Startup Finished!')
        self.logger.info(
            'Note: Discord needs up to an hour to load your global commands / '
            'context menus. They may not appear immediately\n'
        )
