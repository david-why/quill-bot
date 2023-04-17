from interactions import Embed, Color

__all__ = ['error_embed']


def error_embed(message: str):
    return Embed(title='Error', description=message, color=Color.from_rgb(255, 0, 0))
