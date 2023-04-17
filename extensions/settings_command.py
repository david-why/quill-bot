from typing import Optional

from interactions import (
    Extension,
    InteractionContext,
    slash_command,
    ChannelSelectMenu,
    ChannelType,
)
from util import error_embed
from database import Settings
from client import CustomClient


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


def setup(bot: CustomClient):
    SettingsCommandExtension(bot)
