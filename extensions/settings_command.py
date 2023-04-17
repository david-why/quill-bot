from typing import Optional

from interactions import (
    ChannelSelectMenu,
    ChannelType,ComponentContext,
    Embed,
    Extension,
    InteractionContext,
    Permissions,component_callback,
    slash_command,
)

from client import CustomClient
from database import Settings
from util import error_embed


class SettingsCommandExtension(Extension):
    bot: CustomClient

    @slash_command(name='settings', description='Update the server settings for Quill')
    async def settings_command(self, ctx: InteractionContext):
        guild = ctx.guild
        if guild is None:
            await ctx.send(
                embeds=error_embed('/settings can only be used in servers'),
                ephemeral=True,
            )
            return
        member = ctx.member
        if member is None:
            await ctx.send(embeds=error_embed('Unknown error -13'), ephemeral=True)
            return
        if not member.has_permission(Permissions.MANAGE_GUILD):
            await ctx.send(
                embeds=error_embed('You must have the Manage Server permission!'),
                ephemeral=True,
            )
        guild_id = guild.id
        settings = self.bot.database.get_guild_settings(guild_id)

        if settings.quotes_channel:
            channel = guild.get_channel(settings.quotes_channel)
            if channel is None:
                await ctx.send(embeds=error_embed('Unknown error -4'), ephemeral=True)
                return
            if channel.name is None:
                await ctx.send(embeds=error_embed('Unknown error -5'), ephemeral=True)
                return
            channel_text = '#' + channel.name
        else:
            channel_text = '<No channel>'

        select = ChannelSelectMenu(
            channel_types=[ChannelType.GUILD_TEXT],
            placeholder=f'Current: {channel_text}',
            custom_id='settings_channel',
        )
        embed = Embed(
            title='Server settings',
            description='Here you can change settings for the Quill bot.',
        )

        return await ctx.send(embeds=embed, components=select)

    @component_callback('settings_channel')
    async def settings_channel_callback(self, ctx: ComponentContext):
        member = ctx.member
        if member is None:
            await ctx.send(embeds=error_embed('Unknown error -13'), ephemeral=True)
            return
        if not member.has_permission(Permissions.MANAGE_GUILD):
            await ctx.send(
                embeds=error_embed('You must have the Manage Server permission!'),
                ephemeral=True,
            )
        self.bot.logger.info(repr(ctx.kwargs))
        await ctx.send('Feature in development', ephemeral=True)


def setup(bot: CustomClient):
    SettingsCommandExtension(bot)
