from typing import Optional

from interactions import (
    TYPE_MESSAGEABLE_CHANNEL,
    ChannelType,
    Embed,
    EmbedField,
    Extension,
    InteractionContext,
    OptionType,
    SlashCommandOption,
    Timestamp,
    slash_command,
)

from client import CustomClient
from util import error_embed


class QuoteCommandExtension(Extension):
    bot: CustomClient

    def parse_time(self, timestr: str) -> Optional[Timestamp]:
        formats = [
            '%y-%m-%d %H:%M:%S',
            '%y%m%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y%m%d %H:%M:%S',
        ]
        for format in formats:
            try:
                return Timestamp.strptime(timestr, format)
            except:
                pass

    @slash_command(
        name='quote',
        description='Add a quote to the quotebook',
        options=[
            SlashCommandOption(
                name='from',
                type=OptionType.STRING,
                description='The person who said this quote',
            ),
            SlashCommandOption(
                name='quote',
                type=OptionType.STRING,
                description='The quote text',
            ),
            SlashCommandOption(
                name='context',
                type=OptionType.STRING,
                description='The context for this quote (why did they say this)',
                required=False,
            ),
            SlashCommandOption(
                name='channel',
                type=OptionType.CHANNEL,
                description='The channel to send the quote, defaults to server setting',
                required=False,
                channel_types=[ChannelType.GUILD_TEXT],
            )
            # SlashCommandOption(
            #     name='time',
            #     type=OptionType.STRING,
            #     description='The time of the quote (YYYY-MM-DD HH:MM:SS), defaults to now',
            #     required=False,
            # ),
        ],
    )
    async def quote_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        origin: str = args['from']
        quote: str = args['quote']
        if 'time' in args:
            timestr: str = args['time']
            ts = self.parse_time(timestr)
            if ts is None:
                await ctx.send(
                    embeds=error_embed(
                        f'The time string given is unparseable: {timestr!r}'
                    ),
                    ephemeral=True,
                )
                return
        else:
            ts = Timestamp.now()
        context: Optional[str] = args.get('context')
        if 'channel' in args:
            channel: TYPE_MESSAGEABLE_CHANNEL = args['channel']
        else:
            guild = ctx.guild
            if guild is None:
                channel = ctx.channel
            else:
                settings = self.bot.database.get_guild_settings(guild.id)
                if settings is None or settings.quotes_channel is None:
                    channel = ctx.channel
                else:
                    chan = guild.get_channel(settings.quotes_channel)
                    if not isinstance(chan, TYPE_MESSAGEABLE_CHANNEL):
                        await ctx.send(
                            embeds=error_embed('Unknown error -3'), ephemeral=True
                        )
                        return
                    channel = chan
        quoter = ctx.member
        if quoter is None:
            await ctx.send(embeds=error_embed('Unknown error -2'), ephemeral=True)
            return
        fields = []
        if context:
            fields.append(EmbedField('Context', context))
        quote_embed = Embed(
            title=f'Quote by {origin}', description=quote, fields=fields, timestamp=ts
        ).set_footer('Quoter: ' + quoter.display_name, quoter.display_avatar.url)
        # channel = ctx.channel
        await channel.send(embeds=quote_embed)
        await ctx.send(content='Quote sent!', ephemeral=True)
        # await ctx.send(embeds=quote_embed)

    # @component_callback('hello_world_button')
    # async def my_callback(self, ctx: ComponentContext):
    #     await ctx.send('Hiya to you too')


def setup(bot: CustomClient):
    QuoteCommandExtension(bot)
