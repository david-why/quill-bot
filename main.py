#!/usr/bin/env python3
import os

import dotenv
from interactions import Intents
from interactions.client import const as client_const

from client import CustomClient
from loader import load_extensions
from log import init_logging

if 1001 not in client_const.RECOVERABLE_WEBSOCKET_CLOSE_CODES:
    client_const.RECOVERABLE_WEBSOCKET_CLOSE_CODES = (
        *client_const.RECOVERABLE_WEBSOCKET_CLOSE_CODES,
        1001,
    )

dotenv.load_dotenv()
init_logging()

DEBUG = os.getenv('DEBUG') in ['True', 'true', '1']

kwargs = dict(
    activity='/quote | /chat',
    total_shards=int(os.getenv('SHARDS', 1)),
    shard_id=int(os.getenv('SHARD_ID', 0)),
    intents=Intents.DEFAULT | Intents.MESSAGE_CONTENT | Intents.GUILD_MEMBERS,
)

if DEBUG:
    debug_guild_id = os.getenv('DEBUG_GUILD')
    if debug_guild_id is None:
        raise ValueError('DEBUG_GUILD should be set to the server ID to debug in')
    kwargs.update(debug_scope=int(debug_guild_id))
    print(f'using debug_scope={debug_guild_id}')

bot = CustomClient(**kwargs)

load_extensions(bot)

bot.start(os.getenv('DISCORD_TOKEN'))
