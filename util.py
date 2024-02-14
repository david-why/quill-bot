from datetime import timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from interactions import (
    TYPE_CHANNEL_MAPPING,
    TYPE_MESSAGEABLE_CHANNEL,
    Color,
    Embed,
    Member,
    Timestamp,
    User,
)

if TYPE_CHECKING:
    from database import MessageTemplate

__all__ = [
    'MESSAGEABLE_CHANNEL_TYPES',
    'error_embed',
    'tomorrow',
    'build_message',
    'parse_time',
]


_rev_mapping = {v: k for k, v in TYPE_CHANNEL_MAPPING.items()}

MESSAGEABLE_CHANNEL_TYPES = [
    _rev_mapping[t]
    for t in TYPE_MESSAGEABLE_CHANNEL.__args__  # type: ignore
    if t in _rev_mapping
]  # type: list[int]  # i hate vscode


def error_embed(message: str) -> Embed:
    return Embed(title='Error', description=message, color=Color.from_rgb(255, 0, 0))


def tomorrow() -> Timestamp:
    now = Timestamp.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    return tomorrow


def ordinal(number: int) -> str:
    if 11 <= number <= 13:
        return f'{number}th'
    return str(number) + {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')


def _format(text: Optional[str], member: Union[Member, User]) -> Optional[str]:
    if text is None:
        return
    kwargs: Dict[str, Any] = dict(name=member.display_name, mention=member.mention)
    if isinstance(member, Member):
        kwargs.update(
            number=member.guild.member_count,
            ordinal=ordinal(member.guild.member_count),
        )
    return text.format(**kwargs)


def build_message(
    template: 'MessageTemplate', member: Union[Member, User]
) -> Dict[str, Any]:
    kwargs = {}
    if template.content:
        kwargs['content'] = _format(template.content, member)
    if template.title or template.body:
        embed = Embed(
            title=_format(template.title, member),
            description=_format(template.body, member),
        )
        kwargs['embeds'] = embed
    return kwargs


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
        ts -= timedelta(minutes=tzoffset)
        if ts.replace(tzinfo=timezone.utc) < Timestamp.utcnow():
            ts += timedelta(days=1)
        return ts
