from interactions import (
    TYPE_MESSAGEABLE_CHANNEL,
    CommandType,
    ContextMenuContext,
    Embed,
    Extension,
    Message,
    context_menu,
)
from interactions.client.errors import HTTPException

from client import CustomClient
from util import error_embed


class QuoteContextExtension(Extension):
    bot: CustomClient

    @context_menu(name='Quote message', context_type=CommandType.MESSAGE)
    async def quote_context_menu(self, ctx: ContextMenuContext):
        message = ctx.target
        if message is None or not isinstance(message, Message):
            await ctx.send(embeds=error_embed('Unknown error -1'), ephemeral=True)
            return
        origin = message.author
        quote = message.content
        ts = message.timestamp
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
        embed = Embed(
            title=f'Quote by {origin.display_name}',
            description=quote,
            timestamp=ts,
            url=message.jump_url,
        ).set_footer('Quoter: ' + quoter.display_name, quoter.display_avatar.url)
        try:
            await channel.send(content=f'||{origin.mention}||', embeds=embed)
        except HTTPException as exc:
            if exc.status == 403:
                await ctx.send(
                    content='Lack permissions to send in channel', ephemeral=True
                )
            else:
                raise
        else:
            await ctx.send(content='Quote sent!', ephemeral=True)
        # await ctx.send(content=f'||{origin.mention}||', embeds=embed)


def setup(bot: CustomClient):
    QuoteContextExtension(bot)
