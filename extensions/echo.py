from typing import Optional

from interactions import (
    TYPE_MESSAGEABLE_CHANNEL,
    ChannelType,
    Extension,
    InteractionContext,
    OptionType,
    SlashCommandOption,
    slash_command,
)

from client import CustomClient


class EchoCommandExtension(Extension):
    bot: CustomClient

    @slash_command(
        'echo',
        description='Send a plain message',
        options=[
            SlashCommandOption(
                name='message',
                type=OptionType.STRING,
                description='The message for me to send',
            ),
            SlashCommandOption(
                name='channel',
                type=OptionType.CHANNEL,
                description='The channel to send the message',
                channel_types=[ChannelType.GUILD_TEXT],
                required=False,
            ),
        ],
    )
    async def echo_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        message: str = args['message']
        channel: Optional[TYPE_MESSAGEABLE_CHANNEL] = args.get('channel', ctx.channel)
        await channel.send(message.replace('\\n', '\n').replace('\\\\', '\\'))
        await ctx.send('Message sent!', ephemeral=True)


def setup(bot: CustomClient):
    EchoCommandExtension(bot)
