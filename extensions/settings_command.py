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

    async def get_embed_and_components(self, guild: Guild):
        guild_id = guild.id
        settings = self.bot.database.get_guild_settings(guild_id)
        quote_channel = (
            f'<#{settings.quotes_channel}>'
            if settings.quotes_channel
            else '<No channel>'
        )
        starboard_channel = (
            f'<#{settings.starboard_channel}>'
            if settings.starboard_channel
            else '<No channel>'
        )

        quote_field = EmbedField(
            'Quotes channel',
            'The serverwide channel to send /quote and "Quote message" quotes to.\n'
            f'Currently set to {quote_channel}',
        )
        starboard_field = EmbedField(
            'Starboard channel',
            'The channel to send messages with a certain number of stars to.\n'
            f'Currently set to {starboard_channel}',
        )

        quote_select = ChannelSelectMenu(
            channel_types=[ChannelType.GUILD_TEXT],
            custom_id='settings_channel',
            placeholder='Quotes channel',
        )
        starboard_select = ChannelSelectMenu(
            channel_types=[ChannelType.GUILD_TEXT],
            custom_id='settings_starboard',
            placeholder='Starboard channel',
        )
        quote_clear = Button(
            style=ButtonStyle.SECONDARY,
            label='Clear quotes channel',
            custom_id='settings_channel_clear',
        )
        starboard_clear = Button(
            style=ButtonStyle.SECONDARY,
            label='Clear starboard channel',
            custom_id='settings_starboard_clear',
        )
        finish = Button(
            style=ButtonStyle.DANGER,
            label='Exit settings',
            custom_id='settings_exit',
        )

        embed = Embed(
            title='Server settings',
            description='Here you can change settings for the Quill bot.',
            fields=[quote_field, starboard_field],
        )
        return embed, [
            [quote_select],
            [starboard_select],
            [quote_clear, starboard_clear],
            [finish],
        ]

    @slash_command(
        name='settings',
        description='Update the server settings for Quill',
        default_member_permissions=Permissions.MANAGE_GUILD,
        dm_permission=False,
    )
    async def settings_command(self, ctx: InteractionContext):
        guild = ctx.guild
        if guild is None:
            return await ctx.send(
                embeds=error_embed('/settings can only be used in servers'),
                ephemeral=True,
            )
        try:
            embed, components = await self.get_embed_and_components(guild)
        except SettingsError as exc:
            return await ctx.send(embeds=error_embed(exc.msg), ephemeral=True)
        return await ctx.send(
            embeds=embed,
            components=components,
        )

    @component_callback('settings_channel')
    async def settings_channel_callback(self, ctx: ComponentContext):
        guild = ctx.guild
        assert guild
        guild_id = guild.id
        channels = ctx.values
        channel: GuildText = channels[0]  # type: ignore
        settings = self.bot.database.get_guild_settings(guild_id)
        settings.quotes_channel = channel.id
        self.bot.database.set_guild_settings(guild_id, settings)
        embed, components = await self.get_embed_and_components(guild)
        await ctx.edit_origin(embeds=embed, components=components)

    @component_callback('settings_channel_clear')
    async def settings_channel_clear_callback(self, ctx: ComponentContext):
        guild = ctx.guild
        assert guild
        guild_id = guild.id
        settings = self.bot.database.get_guild_settings(guild_id)
        settings.quotes_channel = None
        self.bot.database.set_guild_settings(guild_id, settings)
        embed, components = await self.get_embed_and_components(guild)
        await ctx.edit_origin(embeds=embed, components=components)

    @component_callback('settings_starboard')
    async def settings_starboard_callback(self, ctx: ComponentContext):
        guild = ctx.guild
        assert guild
        guild_id = guild.id
        channels = ctx.values
        channel: GuildText = channels[0]  # type: ignore
        settings = self.bot.database.get_guild_settings(guild_id)
        settings.starboard_channel = channel.id
        self.bot.database.set_guild_settings(guild_id, settings)
        embed, components = await self.get_embed_and_components(guild)
        await ctx.edit_origin(embeds=embed, components=components)

    @component_callback('settings_starboard_clear')
    async def settings_starboard_clear_callback(self, ctx: ComponentContext):
        guild = ctx.guild
        assert guild
        guild_id = guild.id
        settings = self.bot.database.get_guild_settings(guild_id)
        settings.starboard_channel = None
        self.bot.database.set_guild_settings(guild_id, settings)
        embed, components = await self.get_embed_and_components(guild)
        await ctx.edit_origin(embeds=embed, components=components)

    @component_callback('settings_exit')
    async def settings_exit_callback(self, ctx: ComponentContext):
        await ctx.edit_origin(components=[])


def setup(bot: CustomClient):
    SettingsCommandExtension(bot)
