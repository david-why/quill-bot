from interactions import (
    Button,
    ButtonStyle,
    ChannelSelectMenu,
    ChannelType,
    ComponentContext,
    Embed,
    EmbedField,
    Extension,
    Guild,
    GuildText,
    InteractionContext,
    Permissions,
    component_callback,
    slash_command,
)

from client import CustomClient
from util import error_embed


class SettingsError(Exception):
    def __init__(self, msg, *args):
        self.msg = msg
        super().__init__(*args)


class SettingsCommandExtension(Extension):
    bot: CustomClient

    def get_embed_and_components(self, guild: Guild):
        guild_id = guild.id
        settings = self.bot.database.get_guild_settings(guild_id)

        channel = None
        if settings.quotes_channel:
            channel = guild.get_channel(settings.quotes_channel)
            if channel is None:
                raise SettingsError('Unknown error -4')

        channel_field = EmbedField(
            'Quotes channel',
            'The serverwide channel to send /quote and "Quote message" quotes to.\n'
            f'Currently set to {channel.mention if channel else "<No channel>"}',
        )
        channel_select = ChannelSelectMenu(
            channel_types=[ChannelType.GUILD_TEXT],
            custom_id='settings_channel',
            placeholder='Quotes channel',
        )
        channel_clear = Button(
            style=ButtonStyle.SECONDARY,
            label='Clear quotes channel',
            custom_id='settings_channel_clear',
        )
        embed = Embed(
            title='Server settings',
            description='Here you can change settings for the Quill bot.',
            fields=[channel_field],
        )
        return embed, [[channel_select], [channel_clear]]

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
            return

        try:
            embed, components = self.get_embed_and_components(guild)
        except SettingsError as exc:
            await ctx.send(embeds=error_embed(exc.msg), ephemeral=True)
            return

        return await ctx.send(
            embeds=embed,
            components=components,
        )

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
            return
        guild = ctx.guild
        assert guild
        guild_id = guild.id
        channels = ctx.values
        if not channels:
            await ctx.send(embeds=error_embed('Unknown error -14'), ephemeral=True)
            return
        channel: GuildText = channels[0]  # type: ignore
        if not channel:
            await ctx.send(embeds=error_embed('Unknown error -15'), ephemeral=True)
            return
        settings = self.bot.database.get_guild_settings(guild_id)
        settings.quotes_channel = channel.id
        self.bot.database.set_guild_settings(guild_id, settings)
        embed, components = self.get_embed_and_components(guild)
        await ctx.edit_origin(embeds=embed, components=components)
        # await ctx.send(f'Updated quotes channel to {channel.mention}!')

    @component_callback('settings_channel_clear')
    async def settings_channel_clear_callback(self, ctx: ComponentContext):
        member = ctx.member
        if member is None:
            await ctx.send(embeds=error_embed('Unknown error -13'), ephemeral=True)
            return
        if not member.has_permission(Permissions.MANAGE_GUILD):
            await ctx.send(
                embeds=error_embed('You must have the Manage Server permission!'),
                ephemeral=True,
            )
            return
        guild = ctx.guild
        assert guild
        guild_id = guild.id
        settings = self.bot.database.get_guild_settings(guild_id)
        settings.quotes_channel = None
        self.bot.database.set_guild_settings(guild_id, settings)
        embed, components = self.get_embed_and_components(guild)
        await ctx.edit_origin(embeds=embed, components=components)
        # await ctx.send('Cleared quotes channel!')


def setup(bot: CustomClient):
    SettingsCommandExtension(bot)
