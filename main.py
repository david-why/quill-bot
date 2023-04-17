import os

import dotenv

from client import CustomClient
from loader import load_extensions
from log import init_logging

DEBUG = False

dotenv.load_dotenv()
init_logging()

if DEBUG:
    bot = CustomClient(activity='/quote', debug_scope=int(os.getenv('DEBUG_GUILD')))
else:
    bot = CustomClient(activity='/quote')

load_extensions(bot)

bot.start(os.getenv('DISCORD_TOKEN'))
