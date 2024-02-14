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
from util import error_embed, parse_time


class QuoteCommandExtension(Extension):
    bot: CustomClient

    @slash_command(
        name='quote',
        description='Add a quote to the quotebook',
        dm_permission=False,
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
                name='ctx',
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
            ),
            SlashCommandOption(
                name='time',
                type=OptionType.STRING,
                description='The time of the quote (YYYY-MM-DD HH:MM:SS), defaults to now',
                required=False,
            ),
        ],
    )
    async def quote_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        origin: str = args['from']
        quote: str = args['quote']
        if 'time' in args:
            timestr: str = args['time']
            user = self.bot.database.get_user(ctx.user.id)
            if user.timezone is None:
                return await ctx.send(
                    'You need to set your timezone with /usersettings first!',
                    ephemeral=True,
                )
            ts = parse_time(timestr, user.timezone)
            if ts is None:
                return await ctx.send('Cannot parse the time string!', ephemeral=True)
        else:
            ts = Timestamp.now()
        context: Optional[str] = args.get('ctx')
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
            return await ctx.send(embeds=error_embed('Unknown error -2'), ephemeral=True)
        fields = []
        if context:
            fields.append(EmbedField('Context', context))
        quote_embed = Embed(
            title=f'Quote by {origin}', description=quote, fields=fields, timestamp=ts
        ).set_footer('Quoter: ' + quoter.display_name, quoter.display_avatar.url)
        await channel.send(embeds=quote_embed)
        await ctx.send(content='Quote sent!', ephemeral=True)


def setup(bot: CustomClient):
    QuoteCommandExtension(bot)
