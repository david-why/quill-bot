import atexit
import cgi
import json
import re
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from aiohttp import ClientSession
from interactions import (
    ActionRow,
    Button,
    ButtonStyle,
    ComponentContext,
    Embed,
    EmbedField,
    Extension,
    File,
    InteractionContext,
    OptionType,
    SlashCommandOption,
    component_callback,
    slash_command,
)
from markdownify import markdownify as md

from client import CustomClient

BASE_URL = 'https://z-library.se'
SEARCH_LIMIT = '5'

SESSION = None


async def _sess():
    global SESSION
    if SESSION is None:
        SESSION = ClientSession()
        atexit.register(SESSION.close)
    return SESSION


class ZlibCommandExtension(Extension):
    bot: CustomClient

    def _user_zlib_auth(self, user_id: int):
        user = self.bot.database.get_user(user_id)
        if user.zlib_query is None:
            return None
        parsed = parse_qs(user.zlib_query)
        return (
            f'remix_userid={parsed["remix_userid"][0]}; '
            f'remix_userkey={parsed["remix_userkey"][0]}'
        )

    @slash_command(
        'zlib',
        description='Z-library commands',
        sub_cmd_name='auth',
        sub_cmd_description='Log in to Z-library (your credentials are not saved)',
        options=[
            SlashCommandOption(
                'username',
                type=OptionType.STRING,
                description='Username (email) on Z-library',
            ),
            SlashCommandOption(
                'password', type=OptionType.STRING, description='Password on Z-library'
            ),
        ],
    )
    async def auth_command(self, ctx: InteractionContext):
        username = ctx.kwargs['username']
        password = ctx.kwargs['password']
        await ctx.defer(ephemeral=True)
        sess = await _sess()
        async with sess.post(
            f'{BASE_URL}/rpc.php',
            data={
                'isModal': 'true',
                'email': username,
                'password': password,
                'site_mode': 'books',
                'action': 'login',
                'redirectUrl': BASE_URL,
                'gg_json_mode': '1',
            },
        ) as r:
            data = await r.json()
        if data.get('errors') or data['response'].get('validationError'):
            return await ctx.send(
                'Log in failed! Please contact the bot owner with the attachment.',
                files=File(
                    BytesIO(json.dumps(data).encode()),
                    file_name='response.json',
                    content_type='application/json',
                ),
                ephemeral=True,
            )
        url = data['response'].get('priorityRedirectUrl') or data['response'].get(
            'forceRedirection'
        )
        query = urlparse(url).query
        parsed = parse_qs(query)
        if 'remix_userid' not in parsed or 'remix_userkey' not in parsed:
            return await ctx.send(
                'Log in failed! Please contact the bot owner with the attachment.',
                files=File(
                    BytesIO(json.dumps(data).encode()),
                    file_name='response.json',
                    content_type='application/json',
                ),
                ephemeral=True,
            )
        user = self.bot.database.get_user(ctx.user.id)
        user.zlib_query = urlparse(url).query
        self.bot.database.set_user(ctx.user.id, user)
        return await ctx.send(f'Welcome to Z-library, **{username}**!')

    @slash_command(
        'zlib',
        description='Z-library commands',
        sub_cmd_name='search',
        sub_cmd_description='Search for books in Z-library',
        options=[
            SlashCommandOption(
                'keywords',
                type=OptionType.STRING,
                description='Keywords (title, author, etc.) to search',
            )
        ],
    )
    async def search_command(self, ctx: InteractionContext):
        keywords = ctx.kwargs['keywords']
        await ctx.defer()
        sess = await _sess()
        zlib_auth = self._user_zlib_auth(ctx.user.id)
        if zlib_auth is None:
            return await ctx.send(
                'You have not logged in to Z-library yet. Use "/zlib auth" to begin!',
                ephemeral=True,
            )
        async with sess.post(
            f'{BASE_URL}/eapi/book/search',
            data={'message': keywords, 'limit': SEARCH_LIMIT},
            headers={'Cookie': zlib_auth},
        ) as r:
            data = await r.json()
        if not data.get('success'):
            return await ctx.send(
                'Search failed! Please contact the bot owner with the attachment.',
                files=File(
                    BytesIO(json.dumps(data).encode()),
                    file_name='response.json',
                    content_type='application/json',
                ),
                # ephemeral=True,
            )
        fields = []
        components = []
        for i, book in enumerate(data['books']):
            # size = sizeify(int(book.get('filesize')))
            size = book.get('filesizeString') or 'unknown size'
            desc = md(book.get('description') or '')
            value = f'*{book["extension"]}, {size}, {book["language"]}*\n{desc}'
            if len(value) > 1024:
                value = value[:1021] + '...'
            fields.append(EmbedField(f'{i+1}. {book["title"]}', value))
            # url = (ZLIB_BASE + book['dl']) if book.get('dl') else ZLIB_BASE
            custom_id = (
                f'zlibdl:{ctx.user.id}_{book["dl"]}' if book.get('dl') else 'none'
            )
            disabled = not book.get('dl')
            components.append(
                Button(
                    style=ButtonStyle.SECONDARY,
                    label=f'#{i+1}',
                    emoji='⬇️',
                    disabled=disabled,
                    # url=url,
                    custom_id=custom_id,
                )
            )
        return await ctx.send(
            embeds=Embed(f'Search results for: {keywords}', fields=fields),
            components=ActionRow.split_components(*components),
        )

    @component_callback(re.compile(r'zlibdl:[0-9]+_.*'))
    async def zlibdl_component(self, ctx: ComponentContext):
        first, _, path = ctx.custom_id.partition('_')
        uid = int(first.partition(':')[2])
        if uid != ctx.user.id:
            return await ctx.send(
                'You are not the user who searched. Please search again!',
                ephemeral=True,
            )
        zlib_auth = self._user_zlib_auth(ctx.user.id)
        if zlib_auth is None:
            return await ctx.send(
                'You have not logged in to Z-library yet. Use "/zlib auth" to begin!',
                ephemeral=True,
            )
        await ctx.defer(ephemeral=True)
        sess = await _sess()
        async with sess.get(f'{BASE_URL}{path}', headers={'Cookie': zlib_auth}) as r:
            content_type = r.headers.get('Content-Type')
            header = r.headers.get('Content-Disposition')
            filename = 'book.bin'
            if header is not None:
                _, params = cgi.parse_header(header)
                filename = params.get('filename', filename)
            data = await r.read()
        return await ctx.send(
            'Here is your downloaded book!',
            files=File(BytesIO(data), filename, content_type=content_type),
            ephemeral=True,
        )


def setup(bot: CustomClient):
    ZlibCommandExtension(bot)
