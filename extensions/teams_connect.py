import os
import time
from typing import Dict, Tuple, cast

import aiohttp
from discord_markdown.discord_markdown import convert_to_html
from interactions import (
    Button,
    ButtonStyle,
    ComponentContext,
    Embed,
    EmbedField,
    Extension,
    Guild,
    InteractionContext,
    Permissions,
    component_callback,
    listen,
    slash_command,
)
from interactions.api.events import MessageCreate

from client import CustomClient
from graph import Auth, ErrorResponse, LogInResponse, PollResponse
from util import error_embed

auth = None

SCOPES = ['ChatMessage.Read', 'ChatMessage.Send', 'email']


class TeamsConnectorExtension(Extension):
    bot: CustomClient
    database: Dict[int, Tuple[int, LogInResponse]]

    def __init__(self, bot: CustomClient) -> None:
        cast(None, bot)
        self.database = {}

    def get_embed_components(self, guild: Guild):
        guild_id = guild.id
        settings = self.bot.database.get_guild_settings(guild_id)
        teams_auth = settings.teams_auth
        components = []
        auth_status = 'This server is not logged in to Teams.'
        if teams_auth is not None:
            assert auth
            id_data = auth.parse_id_token(teams_auth['id_token'])
            info = id_data.get('email')
            auth_status = f'This server is logged in as **{info}**'
            components.append(
                Button(
                    style=ButtonStyle.DANGER,
                    label='Unauthorize Teams',
                    custom_id='teams_unauth',
                )
            )
        else:
            components.append(
                Button(
                    style=ButtonStyle.PRIMARY,
                    label='Authorize Teams',
                    custom_id='teams_auth',
                )
            )
        channel_name = 'No channel connected'
        channel_id = settings.teams_channel
        if channel_id is not None:
            channel = guild.get_channel(channel_id)
            if channel is not None:
                channel_name = f'Connected to {channel.mention}'
        fields = [
            EmbedField('Auth status', auth_status),
            EmbedField('Connected channel', channel_name),
        ]
        embed = Embed(title='Teams Connector status', fields=fields)
        return embed, components

    @slash_command(
        'teams',
        description='Connect with teams',
        default_member_permissions=Permissions.MANAGE_GUILD,
    )
    async def teams_command(self, ctx: InteractionContext):
        guild = ctx.guild
        if guild is None:
            await ctx.send('You can only do this in a server!', ephemeral=True)
            return
        member = ctx.member
        if member is None:
            await ctx.send(embeds=error_embed('Unknown error -18'), ephemeral=True)
            return
        if not member.has_permission(Permissions.MANAGE_GUILD):
            await ctx.send(
                embeds=error_embed('You do not have the Manage Server permission!'),
                ephemeral=True,
            )
            return
        embed, components = self.get_embed_components(guild)
        await ctx.send(embeds=embed, components=components)

    @component_callback('teams_unauth')
    async def teams_unauth_callback(self, ctx: ComponentContext):
        guild = ctx.guild
        assert guild is not None
        guild_id = guild.id
        member = ctx.member
        if member is None:
            await ctx.send(embeds=error_embed('Unknown error -19'), ephemeral=True)
            return
        if not member.has_permission(Permissions.MANAGE_GUILD):
            await ctx.send(
                embeds=error_embed('You do not have the Manage Server permission!'),
                ephemeral=True,
            )
            return
        settings = self.bot.database.get_guild_settings(guild_id)
        settings.teams_auth = None
        self.bot.database.set_guild_settings(guild_id, settings)
        embed, components = self.get_embed_components(guild)
        await ctx.edit_origin(embeds=embed, components=components)

    @component_callback('teams_auth')
    async def teams_auth_callback(self, ctx: ComponentContext):
        guild = ctx.guild
        assert guild is not None
        guild_id = guild.id
        member = ctx.member
        if member is None:
            await ctx.send(embeds=error_embed('Unknown error -20'), ephemeral=True)
            return
        if guild_id in self.database:
            if time.time() <= self.database[guild_id][1]['expires']:
                await ctx.send(
                    'Another user is authorizing, try again later!', ephemeral=True
                )
        if not member.has_permission(Permissions.MANAGE_GUILD):
            await ctx.send(
                embeds=error_embed('You do not have the Manage Server permission!'),
                ephemeral=True,
            )
            return
        settings = self.bot.database.get_guild_settings(guild_id)
        if settings.teams_auth is not None:
            await ctx.send(
                'Oops, looks like the server is already authorized to Teams!',
                ephemeral=True,
            )
            return
        assert auth
        resp = await auth.log_in(SCOPES)
        if 'error' in resp:
            resp = cast(ErrorResponse, resp)
            msg = 'Oops, an error occurred: '
            msg += resp['error']
            if 'error_description' in resp:
                msg += '\n'
                msg += resp['error_description']
            await ctx.send(embeds=error_embed(msg), ephemeral=True)
            return
        resp = cast(LogInResponse, resp)
        self.database[guild_id] = (ctx.user.id, resp)
        embed = Embed(title='Authorize to Teams', description=resp['message'])
        await ctx.send(embeds=embed, ephemeral=True)
        poll = await auth.poll_log_in(resp)
        if 'error' in poll:
            if self.database.get(guild_id, (0,))[0] != ctx.user.id:
                await ctx.channel.send(
                    embeds=error_embed('Unknown error -21'), reply_to=ctx.message
                )
                return
            poll = cast(ErrorResponse, poll)
            msg = 'Oops, an error occurred: '
            msg += poll['error']
            if 'error_description' in poll:
                msg += '\n'
                msg += poll['error_description']
            await ctx.channel.send(embeds=error_embed(msg), reply_to=ctx.message)
            return
        poll = cast(PollResponse, poll)
        settings = self.bot.database.get_guild_settings(guild_id)
        settings.teams_auth = poll
        self.bot.database.set_guild_settings(guild_id, settings)
        del self.database[guild_id]
        embed, components = self.get_embed_components(guild)
        assert ctx.message
        await ctx.message.edit(embeds=embed, components=components)

    @listen()
    async def on_message_create(self, event: MessageCreate):
        assert auth
        message = event.message
        if not message.guild:
            return
        guild_id = message.guild.id
        channel_id = message.channel.id
        settings = self.bot.database.get_guild_settings(guild_id)
        if (
            settings.teams_channel != channel_id
            or settings.teams_auth is None
            or settings.teams_chat_id is None
        ):
            return
        author = message.author
        author_name = f'{author.display_name}#{author.discriminator}'
        composed = (
            f'<div><p><b>{author_name}</b> <a href="{message.jump_url}"><i>from '
            f'Discord</i></a></p><div>{convert_to_html(message.content)}</div></div>'
        )
        tokens = await auth.get_tokens(settings.teams_auth)
        if 'error' in tokens:
            error = cast(ErrorResponse, tokens)
            desc = error.get('error_description', 'unknown')
            await message.reply(f'Error sending to Teams: {error["error"]}: {desc}')
            return
        if tokens != settings.teams_auth:
            settings = self.bot.database.get_guild_settings(guild_id)
            settings.teams_auth = tokens
            self.bot.database.set_guild_settings(guild_id, settings)
        tokens = cast(PollResponse, tokens)
        token_type = tokens['token_type']
        access_token = tokens['access_token']
        token = f'{token_type} {access_token}'
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'https://graph.microsoft.com/v1.0/chats/{settings.teams_chat_id}/messages',
                json={'body': {'content': composed, 'contentType': 'html'}},
                headers={'Authorization': token},
            ) as resp:
                if resp.status >= 400:
                    await message.reply(
                        f'HTTP error sending to Teams: {resp.status}: {await resp.text()}'
                    )


def setup(bot: CustomClient):
    client_id = os.getenv('GRAPH_CLIENT_ID')
    if client_id is None:
        bot.logger.warning('No GRAPH_CLIENT_ID found, disabling teams_connect')
    else:
        tenant = os.getenv('GRAPH_TENANT', 'common')
        global auth
        auth = Auth(client_id, tenant)
        TeamsConnectorExtension(bot)
