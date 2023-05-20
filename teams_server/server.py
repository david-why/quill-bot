import json
import os
import traceback
from asyncio import Queue, get_event_loop
from datetime import datetime, timedelta
from html import escape as html_escape
from typing import TYPE_CHECKING, cast

from aiohttp import ClientSession
from aiohttp.web import (
    Application,
    AppRunner,
    Request,
    Response,
    RouteTableDef,
    TCPSite,
)
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from interactions import TYPE_MESSAGEABLE_CHANNEL

from graph import Auth
from log import CustomLogger
from teams_server.subscription import (
    GraphError,
    GraphSubscriptions,
    LifecycleNotification,
)

if TYPE_CHECKING:
    from client import CustomClient

CHAT_EXPIRES = timedelta(minutes=59)

load_dotenv()

client_id = os.getenv('GRAPH_CLIENT_ID')
if client_id is None:
    raise ValueError('GRAPH_CLIENT_ID environment variable not found')
# clientState = {'s': client_state, 'g': guild_id, 'c': chat_id}
client_state = os.getenv('GRAPH_CLIENT_STATE', 'this_is_really_secreeet')
# if client_state is None:
#     raise ValueError('GRAPH_CLIENT_STATE environment variable not found')
external_url = os.getenv('TEAMS_EXTERNAL_URL')
if external_url is None:
    raise ValueError('TEAMS_EXTERNAL_URL environment variable not found')


auth = Auth(client_id, os.getenv('GRAPH_TENANT', 'common'))
sub = GraphSubscriptions(client_state, auth)

routes = RouteTableDef()


def build_client_state(guild_id: int, chat_id: str):
    return json.dumps({'s': client_state, 'g': guild_id, 'c': chat_id})


@routes.post('/chatMessageNotification')
async def chat_message_notification(request: Request):
    if 'validationToken' in request.query:
        return Response(text=html_escape(request.query['validationToken']), status=200)
    data = await request.json()
    if (
        not isinstance(data, dict)
        and 'value' in data
        and isinstance(data['value'], list)
    ):
        return Response(status=500)
    for value in data['value']:
        # print('got value', value)
        try:
            client_state_dict = json.loads(value['clientState'])
        except:
            return Response(status=202)
        if client_state_dict.get('s') != client_state:
            return Response(status=202)
        queue: Queue = request.app['CM_QUEUE']
        await queue.put(value)
    return Response(status=202)


@routes.post('/lifecycleNotification')
async def lifecycle_notification(request: Request):
    if 'validationToken' in request.query:
        return Response(text=html_escape(request.query['validationToken']), status=200)
    data = await request.json()
    if (
        not isinstance(data, dict)
        and 'value' in data
        and isinstance(data['value'], list)
    ):
        return Response(status=500)
    for value in data['value']:
        # print('got lvalue', value)
        try:
            client_state_dict = json.loads(value['clientState'])
        except:
            return Response(status=202)
        if client_state_dict.get('s') != client_state:
            return Response(status=202)
        # await scheduler.spawn(lifecycle_parse(value, get_bot(request)))
        queue: Queue = request.app['LF_QUEUE']
        await queue.put(value)
        # print('spawned lparser')
    return Response(status=202)


async def chat_message_parse(value: dict, app: Application):
    bot: 'CustomClient' = app['DISCORD_BOT']
    odata_id = value['resourceData']['@odata.id']
    client_state_dict = json.loads(value['clientState'])
    subscription_id = value['subscriptionId']
    guild_id = client_state_dict.get('g')
    chat_id = client_state_dict.get('c')
    if guild_id is None or chat_id is None:
        return
    settings = bot.database.get_guild_settings(guild_id)
    if settings.teams_auth is None:
        return
    tokens = await auth.get_tokens(settings.teams_auth)
    if 'error' in tokens:
        return app.logger.warning(f'Error in CM parse refresh: {tokens}')
    if tokens != settings.teams_auth:
        settings.teams_auth = tokens
        bot.database.set_guild_settings(guild_id, settings)
    if settings.teams_chat_id != chat_id:
        return await sub.remove_subscription(tokens, subscription_id)
    if settings.teams_channel is None:
        return
    async with ClientSession(
        headers={'Authorization': 'Bearer ' + tokens['access_token']}
    ) as session:
        async with session.get(f'https://graph.microsoft.com/v1.0/{odata_id}') as resp:
            status = resp.status
            data = await resp.json()
    if status != 200:
        return app.logger.warning(
            f'HTTP status {status} fetching message {odata_id}: {data}'
        )
    if 'body' not in data:
        return app.logger.warning(f'No body found for {odata_id}: {data}')
    sender = data['from']
    if not sender['user']:
        return
    user_name = sender['user']['displayName']
    body = data['body']
    if '<i>from Discord</i></a>' in body['content']:
        return
    if body['contentType'] == 'html':
        # TODO Parse HTML
        soup = BeautifulSoup(body['content'], 'html.parser')
        message = soup.text
    elif body['contentType'] == 'text':
        message = body['content']
    else:
        return app.logger.warning(f'Unknown contentType: {body}')
    guild = await bot.fetch_guild(guild_id)
    if guild is None:
        return await sub.remove_subscription(tokens, subscription_id)
    channel = await guild.fetch_channel(settings.teams_channel)
    if not isinstance(channel, TYPE_MESSAGEABLE_CHANNEL):
        settings.teams_channel = None
        return bot.database.set_guild_settings(guild_id, settings)
    await channel.send(f'**{user_name}** _from Teams_\n{message}')


async def lifecycle_parse(value: dict, app: Application):
    bot: 'CustomClient' = app['DISCORD_BOT']
    client_state_dict = json.loads(value['clientState'])
    guild_id = client_state_dict.get('g')
    if guild_id is None:
        return app.logger.error(f'Guild id missing: {value}')
    subscription_id = value['subscriptionId']
    settings = bot.database.get_guild_settings(guild_id)
    if settings.teams_auth is None or settings.teams_chat_id is None:
        return
    tokens = await auth.get_tokens(settings.teams_auth)
    if 'error' in tokens:
        return app.logger.error(f'Error in refresh for {guild_id}: {tokens}')
    if tokens != settings.teams_auth:
        settings.teams_auth = tokens
        bot.database.set_guild_settings(guild_id, settings)
    sub_chat_id = client_state_dict.get('c')
    if settings.teams_chat_id != sub_chat_id:
        return await sub.remove_subscription(tokens, subscription_id)
    try:
        await sub.parse_lifecycle_notification(
            tokens,
            cast(LifecycleNotification, value),
            notification_url=external_url + '/chatMessageNotification',
            resource=f'/chats/{settings.teams_chat_id}/messages',
            expiration=datetime.utcnow() + CHAT_EXPIRES,
            client_state=build_client_state(guild_id, settings.teams_chat_id),
            lifecycle_notification_url=external_url + '/lifecycleNotification',
        )
    except GraphError:
        app.logger.exception(f'Error parsing lifecycle notification')


async def chat_message_background(queue: Queue, app: Application):
    while True:
        item = await queue.get()
        try:
            await chat_message_parse(item, app)
        except:
            app.logger.exception(f'Error parsing chatMessage {item}')


async def lifecycle_background(queue: Queue, app: Application):
    while True:
        item = await queue.get()
        try:
            await lifecycle_parse(item, app)
        except:
            app.logger.exception(f'Error parsing lifecycle event {item}')


def build_app(bot: 'CustomClient') -> Application:
    logger = CustomLogger().make_logger('teams_server')
    app = Application(logger=logger)
    app.add_routes(routes)
    app['DISCORD_BOT'] = bot
    app['CM_QUEUE'] = cm_queue = Queue()
    app['LF_QUEUE'] = lf_queue = Queue()
    cm_coro = chat_message_background(cm_queue, app)
    lf_coro = lifecycle_background(lf_queue, app)
    loop = get_event_loop()
    cm_task = loop.create_task(cm_coro)
    lf_task = loop.create_task(lf_coro)

    async def on_cleanup(app: Application):
        cast(None, app)
        yield
        logger.info('Shutting down Teams server, canceling daemons...')
        cm_task.cancel()
        lf_task.cancel()

    app.cleanup_ctx.append(on_cleanup)
    return app


async def start_app(app: Application) -> None:
    runner = AppRunner(app, access_log=app.logger)
    await runner.setup()
    site = TCPSite(runner, host='127.0.0.1', port=8083)
    await site.start()
    app.logger.info('Teams connect server started!')
