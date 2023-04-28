from typing import Optional

from interactions import (
    Extension,
    InteractionContext,
    ChannelType,
    TYPE_MESSAGEABLE_CHANNEL,
    slash_command,
    Embed,
    EmbedAuthor,
    SlashCommandOption,
    OptionType,
)

from client import CustomClient


class EmbedCommandExtension(Extension):
    bot: CustomClient

    @slash_command(
        'embed',
        description='Create an embed',
        options=[
            SlashCommandOption(
                name='title',
                type=OptionType.STRING,
                description='Title of the embed',
            ),
            SlashCommandOption(
                name='content',
                type=OptionType.STRING,
                description='The body content of the embed (use \\n for newline)',
            ),
            SlashCommandOption(
                name='channel',
                type=OptionType.CHANNEL,
                description='The channel to send the embed in',
                required=False,
                channel_types=[ChannelType.GUILD_TEXT],
            ),
            SlashCommandOption(
                name='color',
                type=OptionType.STRING,
                description='Hex color code of the embed color',
                required=False,
            ),
        ],
    )
    async def embed_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        title: str = args['title']
        content: str = args['content']
        channel: TYPE_MESSAGEABLE_CHANNEL = args.get('channel', ctx.channel)
        color: Optional[str] = args.get('color')
        member = ctx.member or ctx.user
        embed = Embed(
            title=title,
            description=content.replace('\\n', '\n').replace('\\\\', '\\'),
            color=color,
            author=EmbedAuthor(
                name=member.display_name,
                icon_url=member.display_avatar.url,
            ),
        )
        message = await channel.send(embeds=embed)
        await ctx.send(f'Embed sent! {message.jump_url}')


def setup(bot: CustomClient):
    EmbedCommandExtension(bot)
