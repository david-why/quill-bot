from typing import Optional

from interactions import (
    TYPE_MESSAGEABLE_CHANNEL,
    ChannelType,
    Embed,
    Extension,
    GuildText,
    InteractionContext,
    OptionType,
    Permissions,
    SlashCommandOption,
    listen,
    slash_command,
)
from interactions.api.events import MemberAdd, MemberRemove

from client import CustomClient
from database import MessageTemplate
from util import build_message


class GreetExtension(Extension):
    bot: CustomClient

    @slash_command(
        'greet',
        description='Manages the welcome and goodbye messages',
        default_member_permissions=Permissions.MANAGE_GUILD,
        dm_permission=False,
        options=[
            SlashCommandOption(
                name='channel',
                type=OptionType.CHANNEL,
                description='The channel to send welcome and goodbye messages in',
                channel_types=[ChannelType.GUILD_TEXT],
                required=False,
            ),
            SlashCommandOption(
                name='welcometext',
                type=OptionType.STRING,
                description='The plain text to send to welcome new members',
                required=False,
            ),
            SlashCommandOption(
                name='welcometitle',
                type=OptionType.STRING,
                description='The embed title to send to welcome new members',
                required=False,
            ),
            SlashCommandOption(
                name='welcomebody',
                type=OptionType.STRING,
                description='The embed body to send to welcome new members',
                required=False,
            ),
            SlashCommandOption(
                name='welcomedelete',
                type=OptionType.BOOLEAN,
                description='Delete the welcome message',
                required=False,
            ),
            SlashCommandOption(
                name='goodbyetext',
                type=OptionType.STRING,
                description='The plain text to send when a member leaves',
                required=False,
            ),
            SlashCommandOption(
                name='goodbyetitle',
                type=OptionType.STRING,
                description='The embed title to send when a member leaves',
                required=False,
            ),
            SlashCommandOption(
                name='goodbyebody',
                type=OptionType.STRING,
                description='The embed body to send when a member leaves',
                required=False,
            ),
            SlashCommandOption(
                name='goodbyedelete',
                type=OptionType.BOOLEAN,
                description='Delete the goodbye message',
                required=False,
            ),
        ],
    )
    async def greet_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        channel: Optional[GuildText] = args.get('channel')
        welcome_text: Optional[str] = args.get('welcometext')
        welcome_title: Optional[str] = args.get('welcometitle')
        welcome_body: Optional[str] = args.get('welcomebody')
        welcome_delete: bool = args.get('welcomedelete', False)
        goodbye_text: Optional[str] = args.get('goodbyetext')
        goodbye_title: Optional[str] = args.get('goodbyetitle')
        goodbye_body: Optional[str] = args.get('goodbyebody')
        goodbye_delete: bool = args.get('goodbyedelete', False)
        if not args:
            return await ctx.send('Nothing to update!', ephemeral=True)
        guild = ctx.guild
        if guild is None:
            return await ctx.send('You can only use this in a server!', ephemeral=True)
        settings = self.bot.database.get_guild_settings(guild.id)
        if channel is not None:
            settings.greet_channel = channel.id
        if any(x is not None for x in [welcome_text, welcome_title, welcome_body]):
            template = settings.welcome_msg
            if template is None:
                template = MessageTemplate(welcome_text, welcome_title, welcome_body)
            if welcome_text is not None:
                template.content = welcome_text.replace('\\n', '\n').replace(
                    '\\\\', '\\'
                )
            if welcome_title is not None:
                template.title = welcome_title
            if welcome_body is not None:
                template.body = welcome_body.replace('\\n', '\n').replace('\\\\', '\\')
            settings.welcome_msg = template
        if welcome_delete:
            settings.welcome_msg = None
        if any(x is not None for x in [goodbye_text, goodbye_title, goodbye_body]):
            template = settings.goodbye_msg
            if template is None:
                template = MessageTemplate(goodbye_text, goodbye_title, goodbye_body)
            if goodbye_text is not None:
                template.content = goodbye_text.replace('\\n', '\n').replace(
                    '\\\\', '\\'
                )
            if goodbye_title is not None:
                template.title = goodbye_title
            if goodbye_body is not None:
                template.body = goodbye_body.replace('\\n', '\n').replace('\\\\', '\\')
            settings.goodbye_msg = template
        if goodbye_delete:
            settings.goodbye_msg = None

        greet_channel = '<not set>'
        if settings.greet_channel is not None:
            gr_channel = await guild.fetch_channel(settings.greet_channel)
            if gr_channel is None:
                settings.greet_channel = None
            else:
                greet_channel = gr_channel.mention
        embed = Embed(
            title='Updated greeting messages!',
            description=f'Greet messages are now sent to {greet_channel}\n',
        )

        self.bot.database.set_guild_settings(guild.id, settings)
        await ctx.send(embeds=embed)

    @listen()
    async def on_member_add(self, event: MemberAdd):
        guild = event.guild
        member = event.member
        settings = self.bot.database.get_guild_settings(guild.id)
        if settings.welcome_msg and settings.greet_channel:
            channel = await guild.fetch_channel(settings.greet_channel)
            if isinstance(channel, TYPE_MESSAGEABLE_CHANNEL):
                await channel.send(**build_message(settings.welcome_msg, member))

    @listen()
    async def on_member_remove(self, event: MemberRemove):
        guild = event.guild
        member = event.member
        settings = self.bot.database.get_guild_settings(guild.id)
        if settings.goodbye_msg and settings.greet_channel:
            channel = await guild.fetch_channel(settings.greet_channel)
            if isinstance(channel, TYPE_MESSAGEABLE_CHANNEL):
                await channel.send(**build_message(settings.goodbye_msg, member))


def setup(bot: CustomClient):
    GreetExtension(bot)
