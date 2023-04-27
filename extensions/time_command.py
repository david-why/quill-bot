from datetime import datetime, timedelta, timezone
from typing import Optional

from interactions import (
    Embed,
    Extension,
    InteractionContext,
    OptionType,
    SlashCommandOption,
    Timestamp,
    slash_command,
)

from client import CustomClient


class TimeCommandExtension(Extension):
    bot: CustomClient

    @staticmethod
    def parse_time(time: str, tzoffset: int) -> Optional[Timestamp]:
        try:
            try:
                ts = Timestamp.strptime(time, '%Y-%m-%d %H:%M:%S')
            except:
                ts = Timestamp.strptime(time, '%Y-%m-%d %H:%M')
        except:
            pass
        else:
            return ts - timedelta(minutes=tzoffset)
        try:
            try:
                ts = Timestamp.strptime(time, '%H:%M:%S')
            except:
                ts = Timestamp.strptime(time, '%H:%M').replace(second=0)
        except:
            pass
        else:
            now = Timestamp.utcnow()
            ts = ts.replace(year=now.year, month=now.month, day=now.day)
            print('timestamp', datetime.__repr__(ts))
            ts -= timedelta(minutes=tzoffset)
            print('deltad', datetime.__repr__(ts))
            if ts.replace(tzinfo=timezone.utc) < Timestamp.utcnow():
                ts += timedelta(days=1)
            print('utcnow', datetime.utcnow())
            return ts

    @slash_command(
        'time',
        description='Display an embed containing the time in '
        "each user\'s local time",
        options=[
            SlashCommandOption(
                'time',
                type=OptionType.STRING,
                description='The time to display in the format [YYYY-MM-DD] HH:MM[:SS]',
                required=False,
            ),
            SlashCommandOption(
                'description',
                type=OptionType.STRING,
                description='The text to display in the embed',
                required=False,
            ),
            SlashCommandOption(
                'title',
                type=OptionType.STRING,
                description='The title of the embed',
                required=False,
            ),
        ],
    )
    async def time_command(self, ctx: InteractionContext):
        member = ctx.member
        assert member
        args = ctx.kwargs
        time_string: Optional[str] = args.get('time')
        description: str = args.get('description', f'{member.mention} shared the time!')
        title: str = args.get('title', 'Time info')
        user_id = ctx.user.id
        user = self.bot.database.get_user(user_id)
        if time_string is None:
            ts = Timestamp.utcnow()
        else:
            if user.timezone is None:
                await ctx.send(
                    'You need to set your timezone with /usersettings first!',
                    ephemeral=True,
                )
                return
            ts = self.parse_time(time_string, user.timezone)
            if ts is None:
                await ctx.send('Cannot parse the time string!', ephemeral=True)
                return
        embed = Embed(title=title, description=description, timestamp=ts)
        await ctx.send(embeds=embed)


def setup(bot: CustomClient):
    TimeCommandExtension(bot)
