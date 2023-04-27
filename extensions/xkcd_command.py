import json
import random
import re
from typing import Optional

import aiohttp
from interactions import (
    Button,
    ButtonStyle,
    ComponentContext,
    Embed,
    EmbedAttachment,
    Extension,
    InteractionContext,
    OptionType,
    SlashCommandOption,
    Timestamp,
    component_callback,
    slash_command,
)

from client import CustomClient
from util import error_embed


class XKCDError(RuntimeError):
    def __init__(self, msg: str, *args: object) -> None:
        self.msg = msg
        super().__init__(*args)


class XKCD:
    def __init__(self, data: dict):
        self.id = data['num']
        self.title = data['title']
        self.time = Timestamp(
            year=int(data['year']), month=int(data['month']), day=int(data['day'])
        )
        self.alt = data['alt']
        self.img = data['img']
        self.link = f'https://xkcd.com/{self.id}/'

    @classmethod
    async def fetch(cls, id: Optional[int] = None) -> 'XKCD':
        path = f'https://xkcd.com/info.0.json'
        if id is not None:
            path = f'https://xkcd.com/{id}/info.0.json'
        async with aiohttp.ClientSession() as session:
            resp = await session.get(path)
            if resp.status == 404:
                raise XKCDError(f'XKCD {id} not found!')
            if resp.status != 200:
                raise XKCDError(f'HTTP error {resp.status}')
            data = await resp.read()
        info = json.loads(data)
        return cls(info)


class XKCDCommandExtension(Extension):
    bot: CustomClient

    @slash_command(
        name='xkcd',
        description='Fetch an XKCD comic',
        options=[
            SlashCommandOption(
                name='id',
                type=OptionType.INTEGER,
                description='The comic ID, default latest',
                required=False,
            ),
            SlashCommandOption(
                name='random',
                type=OptionType.BOOLEAN,
                description='Fetch a random comic',
                required=False,
            ),
        ],
    )
    async def xkcd_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        id: Optional[int] = args.get('id')
        rand: bool = args.get('random', False)
        if rand:
            latest = await XKCD.fetch()
            id = random.randint(1, latest.id)
        try:
            comic = await XKCD.fetch(id)
        except XKCDError as exc:
            await ctx.send(embeds=error_embed(exc.msg), ephemeral=True)
            return
        embed = Embed(
            title=f'XKCD #{comic.id}: {comic.title}',
            images=[EmbedAttachment(comic.img)],
            # description=comic.alt,
            url=comic.link,
        ).set_footer(f'{comic.time.year}-{comic.time.month:02}-{comic.time.day:02}')
        prev = Button(
            style=ButtonStyle.PRIMARY,
            label='Previous',
            emoji=':arrow_left:',
            custom_id='xkcd_prev',
        )
        randc = Button(
            style=ButtonStyle.SECONDARY,
            label='Random',
            emoji=':game_die:',
            custom_id='xkcd_rand',
        )
        next = Button(
            style=ButtonStyle.PRIMARY,
            label='Next',
            emoji=':arrow_right:',
            custom_id='xkcd_next',
        )
        show = Button(
            style=ButtonStyle.SECONDARY, label='Show alt text', custom_id='xkcd_show'
        )
        await ctx.send(embeds=embed, components=[[prev, randc, next], [show]])

    @component_callback('xkcd_prev', 'xkcd_rand', 'xkcd_next')
    async def xkcd_page_callback(self, ctx: ComponentContext):
        # print('defer')
        # self.bot.logger.info('defer')
        # await ctx.defer(edit_origin=True)
        msg = ctx.message
        if msg is None:
            await ctx.send(embeds=error_embed('Unknown error -6'), ephemeral=True)
            return
        if ctx.guild is not None:
            member = ctx.member
            if member is None:
                await ctx.send(embeds=error_embed('Unknown error -7'), ephemeral=True)
                return
            interaction = msg.interaction
            if interaction is None:
                await ctx.send(embeds=error_embed('Unknown error -11'), ephemeral=True)
                return
            # interact_user = await interaction.user()
            interact_user = self.bot.get_user(interaction._user_id)
            if interact_user is None:
                await ctx.send(embeds=error_embed('Unknown error -12'), ephemeral=True)
                return
            if interact_user.id != member.id:
                await ctx.send(
                    embeds=error_embed('Please do not click that! Not yours!'),
                    ephemeral=True,
                )
                return
        embeds = msg.embeds
        if not embeds:
            await ctx.send(embeds=error_embed('Unknown error -8'), ephemeral=True)
            return
        embed = embeds[0]
        title = embed.title
        if title is None:
            await ctx.send(embeds=error_embed('Unknown error -9'), ephemeral=True)
            return
        match = re.match('XKCD #([0-9]+):', title)
        if match is None:
            await ctx.send(embeds=error_embed('Unknown error -10'), ephemeral=True)
            return
        id = int(match.group(1))
        if ctx.custom_id == 'xkcd_prev':
            id -= 1
        elif ctx.custom_id == 'xkcd_next':
            id += 1
        else:
            latest = await XKCD.fetch()
            id = random.randint(1, latest.id)
        try:
            comic = await XKCD.fetch(id)
        except XKCDError as exc:
            await ctx.send(embeds=error_embed(exc.msg), ephemeral=True)
            return
        embed = Embed(
            title=f'XKCD #{comic.id}: {comic.title}',
            images=[EmbedAttachment(comic.img)],
            # description=comic.alt,
            url=comic.link,
        ).set_footer(f'{comic.time.year}-{comic.time.month:02}-{comic.time.day:02}')
        await ctx.edit_origin(embeds=embed)

    @component_callback('xkcd_show')
    async def xkcd_show_callback(self, ctx: ComponentContext):
        msg = ctx.message
        if msg is None:
            await ctx.send(embeds=error_embed('Unknown error -6'), ephemeral=True)
            return
        embeds = msg.embeds
        if not embeds:
            await ctx.send(embeds=error_embed('Unknown error -8'), ephemeral=True)
            return
        embed = embeds[0]
        title = embed.title
        if title is None:
            await ctx.send(embeds=error_embed('Unknown error -9'), ephemeral=True)
            return
        match = re.match('XKCD #([0-9]+):', title)
        if match is None:
            await ctx.send(embeds=error_embed('Unknown error -10'), ephemeral=True)
            return
        id = int(match.group(1))
        try:
            comic = await XKCD.fetch(id)
        except XKCDError as exc:
            await ctx.send(embeds=error_embed(exc.msg), ephemeral=True)
            return
        button = Button(
            style=ButtonStyle.SECONDARY,
            label='Show to everyone',
            custom_id='xkcd_show_alt',
        )
        await ctx.send(comic.alt, components=[button], reply_to=msg, ephemeral=True)

    @component_callback('xkcd_show_alt')
    async def xkcd_show_alt_callback(self, ctx: ComponentContext):
        msg = ctx.message
        if msg is None:
            await ctx.send(embeds=error_embed('Unknown error -16'), ephemeral=True)
            return
        await ctx.send(msg.content, reply_to=msg.get_referenced_message())


def setup(bot: CustomClient):
    XKCDCommandExtension(bot)
