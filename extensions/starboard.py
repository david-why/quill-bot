from typing import cast

from interactions import Embed, EmbedAuthor, Extension, GuildText, Message, listen
from interactions.api.events import (
    MessageDelete,
    MessageReactionAdd,
    MessageReactionRemove,
)

from client import CustomClient

LIMIT = 1


class StarboardExtension(Extension):
    bot: CustomClient

    async def get_embed_from_message(self, message: Message):
        return Embed(
            description=message.content,
            timestamp=message.timestamp,
            author=EmbedAuthor(
                message.author.display_name,
                icon_url=message.author.display_avatar.url,
            ),
        )

    @listen()
    async def on_reaction_add(self, event: MessageReactionAdd):
        message = event.message
        guild = message.guild
        count = event.reaction_count
        if (
            guild is None
            or event.emoji.id is not None
            or (event.emoji.name != 'star' and event.emoji.name != '⭐')
            or count < LIMIT
        ):
            return
        settings = self.bot.database.get_guild_settings(guild.id)
        if settings.starboard_channel is None:
            return
        channel = cast(GuildText, await guild.fetch_channel(settings.starboard_channel))
        if channel is None:
            settings.starboard_channel = None
            self.bot.database.set_guild_settings(guild.id, settings)
            return
        star_message_id = self.bot.database.get_starboard_message(guild.id, message.id)
        content = ':star: **%d** | %s' % (count, message.jump_url)
        if star_message_id is not None:
            star_message = await channel.fetch_message(star_message_id)
            if star_message is None:
                star_message_id = None
            else:
                await star_message.edit(content=content)
        if star_message_id is None:
            send = await channel.send(
                content, embeds=await self.get_embed_from_message(message)
            )
            self.bot.database.add_starboard_message(guild.id, message.id, send.id)

    @listen()
    async def on_reaction_remove(self, event: MessageReactionRemove):
        message = event.message
        guild = message.guild
        count = event.reaction_count
        if (
            guild is None
            or event.emoji.id is not None
            or (event.emoji.name != 'star' and event.emoji.name != '⭐')
        ):
            return
        settings = self.bot.database.get_guild_settings(guild.id)
        if settings.starboard_channel is None:
            return
        channel = cast(GuildText, await guild.fetch_channel(settings.starboard_channel))
        if channel is None:
            settings.starboard_channel = None
            self.bot.database.set_guild_settings(guild.id, settings)
            return
        star_message_id = self.bot.database.get_starboard_message(guild.id, message.id)
        if star_message_id is None:
            return
        star_message = await channel.fetch_message(star_message_id)
        if star_message is None:
            self.bot.database.delete_starboard_message(guild.id, message.id)
            return
        await star_message.edit(
            content=':star: **%d** | %s' % (count, message.jump_url)
        )

    @listen()
    async def on_delete(self, event: MessageDelete):
        message = event.message
        guild = message.guild
        if guild is None:
            return
        settings = self.bot.database.get_guild_settings(guild.id)
        if settings.starboard_channel is None:
            return
        channel = cast(GuildText, await guild.fetch_channel(settings.starboard_channel))
        if channel is None:
            settings.starboard_channel = None
            self.bot.database.set_guild_settings(guild.id, settings)
            return
        star_message_id = self.bot.database.get_starboard_message(guild.id, message.id)
        if star_message_id is None:
            return
        star_message = await channel.fetch_message(star_message_id)
        if star_message is None:
            self.bot.database.delete_starboard_message(guild.id, message.id)
            return
        await star_message.delete()
        self.bot.database.delete_starboard_message(guild.id, message.id)


def setup(bot: CustomClient):
    StarboardExtension(bot)
