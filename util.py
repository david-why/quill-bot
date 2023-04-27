from interactions import Embed, Color, Timestamp
from datetime import timedelta

__all__ = ['error_embed', 'tomorrow']


def error_embed(message: str) -> Embed:
    return Embed(title='Error', description=message, color=Color.from_rgb(255, 0, 0))


def tomorrow() -> Timestamp:
    now = Timestamp.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    return tomorrow
