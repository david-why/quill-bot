from typing import Optional

from interactions import (
    Extension,
    InteractionContext,
    ChannelType,EmbedAttachment,
    EmbedFooter,
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
            SlashCommandOption(
                name='footer',
                type=OptionType.STRING,
                description='Text that goes in the footer',
                required=False,
            ),
            SlashCommandOption(
                name='footericon',
                type=OptionType.STRING,
                description='URL of icon that goes before the footer text',
                required=False,
            ),
            SlashCommandOption(
                name='image',
                type=OptionType.STRING,
                description='URL of large image to the right',
                required=False
            ),
        ],
    )
    async def embed_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        title: str = args['title']
        content: str = args['content']
        channel: TYPE_MESSAGEABLE_CHANNEL = args.get('channel', ctx.channel)
        color: Optional[str] = args.get('color')
        footer_text: Optional[str] = args.get('footer')
        footer_icon: Optional[str] = args.get('footericon')
        image: Optional[str] = args.get('image')
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
        if footer_text or footer_icon:
            if footer_text is None:
                return await ctx.send(
                    'You cannot have footer icon but not text!', ephemeral=True
                )
            embed.footer = EmbedFooter(footer_text, footer_icon)
        if image:
            embed.thumbnail = EmbedAttachment(image)
        message = await channel.send(embeds=embed)
        await ctx.send(f'Embed sent! {message.jump_url}')


def setup(bot: CustomClient):
    EmbedCommandExtension(bot)
