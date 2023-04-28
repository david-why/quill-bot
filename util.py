from datetime import timedelta
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from interactions import Color, Embed, Member, Timestamp, User

if TYPE_CHECKING:
    from database import MessageTemplate

__all__ = ['error_embed', 'tomorrow']


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
