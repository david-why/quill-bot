from typing import Optional

from interactions import (
    TYPE_MESSAGEABLE_CHANNEL,
    Extension,
    InteractionContext,
    OptionType,
    SlashCommandChoice,
    SlashCommandOption,
    Timestamp,
    slash_command,
)

from client import CustomClient
from util import MESSAGEABLE_CHANNEL_TYPES, parse_time

formats = {
    'd': '12/25/2000',
    'f': 'December 25, 2000 8:00 AM',
    't': '8:00 AM',
    'D': 'December 25, 2000',
    'F': 'Monday, December 25, 2000 8:00 AM',
    'R': '22 years ago',
    'T': '8:00:00 AM',
}


class TimeCommandExtension(Extension):
    bot: CustomClient

    @slash_command(
        'time',
        description='Send a message containing the time in each user\'s local time',
        dm_permission=False,
        options=[
            SlashCommandOption(
                'time',
                type=OptionType.STRING,
                description='The time to display in the format [YYYY-MM-DD] HH:MM[:SS]',
                required=False,
            ),
            SlashCommandOption(
                'format',
                type=OptionType.STRING,
                description='The format to display, defaults to date and time',
                choices=[SlashCommandChoice(v, k) for k, v in formats.items()],
                required=False,
            ),
            SlashCommandOption(
                'text',
                type=OptionType.STRING,
                description='The text to send with the time (use {time} for the time)',
                required=False,
            ),
            SlashCommandOption(
                'channel',
                type=OptionType.CHANNEL,
                description='The channel to send the message in (default: this channel)',
                channel_types=MESSAGEABLE_CHANNEL_TYPES,
                required=False,
            ),
            SlashCommandOption(
                'utc',
                type=OptionType.BOOLEAN,
                description='Whether the time is in UTC (default: your local time)',
                required=False,
            ),
            SlashCommandOption(
                'year',
                type=OptionType.INTEGER,
                description='The year of time',
                required=False,
            ),
            SlashCommandOption(
                'month',
                type=OptionType.INTEGER,
                description='The month of time',
                required=False,
            ),
            SlashCommandOption(
                'day',
                type=OptionType.INTEGER,
                description='The day of time',
                required=False,
            ),
            SlashCommandOption(
                'hour',
                type=OptionType.INTEGER,
                description='The hour of time',
                required=False,
            ),
            SlashCommandOption(
                'minute',
                type=OptionType.INTEGER,
                description='The minute of time',
                required=False,
            ),
            SlashCommandOption(
                'second',
                type=OptionType.INTEGER,
                description='The second of time',
                required=False,
            ),
        ],
    )
    async def time_command(self, ctx: InteractionContext):
        ts = Timestamp.utcnow()
        args = ctx.kwargs
        time: Optional[str] = args.get('time')
        utc: bool = args.get('utc', False)
        if time is not None:
            user = self.bot.database.get_user(ctx.user.id)
            if utc:
                tzoffset = 0
            else:
                if user.timezone is None:
                    return await ctx.send(
                        'Please set your timezone with /usersettings first!',
                        ephemeral=True,
                    )
                tzoffset = user.timezone
            ts = parse_time(time, tzoffset)
            if ts is None:
                return await ctx.send('Unknown time format!', ephemeral=True)
        format: str = args.get('format', 'f')
        text: str = args.get('text', ':clock12: {time}')
        channel: TYPE_MESSAGEABLE_CHANNEL = args.get('channel', ctx.channel)
        year: int = args.get('year', ts.year)
        month: int = args.get('month', ts.month)
        day: int = args.get('day', ts.day)
        hour: int = args.get('hour', ts.hour)
        minute: int = args.get('minute', ts.minute)
        second: int = args.get('second', ts.second)
        ts = ts.replace(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second,
        )
        await channel.send(text.format(time='<t:%d:%s>' % (ts.timestamp(), format)))
        await ctx.send('Message sent!', ephemeral=True)


def setup(bot: CustomClient):
    TimeCommandExtension(bot)
