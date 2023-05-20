import requests
from io import BytesIO
from interactions import (
    TYPE_MESSAGEABLE_CHANNEL,
    Attachment,
    Extension,
    Guild,
    InteractionContext,
    OptionType,
    PartialEmoji,
    Permissions,
    SlashCommandOption,
    Snowflake_Type,
    slash_command,
)
from interactions.client.errors import HTTPException

from client import CustomClient


class ReactCommandExtension(Extension):
    bot: CustomClient

    async def find_message(self, guild: Guild, message_id: Snowflake_Type):
        for channel in guild.channels:
            if not isinstance(channel, TYPE_MESSAGEABLE_CHANNEL):
                continue
            message = channel.get_message(message_id)
            if message is not None:
                return message
        fetched = await guild.fetch_channels()
        for channel in fetched:
            if not isinstance(channel, TYPE_MESSAGEABLE_CHANNEL):
                continue
            message = channel.get_message(message_id)
            if message is not None:
                return message
        for channel in fetched:
            if not isinstance(channel, TYPE_MESSAGEABLE_CHANNEL):
                continue
            message = await channel.fetch_message(message_id)
            if message is not None:
                return message

    @slash_command(
        'react',
        description='React to a message',
        options=[
            SlashCommandOption(
                name='message',
                type=OptionType.STRING,
                description='Message ID to react to',
            ),
            SlashCommandOption(
                name='emoji',
                type=OptionType.STRING,
                description='Emoji to react with',
            ),
        ],
        default_member_permissions=Permissions.MANAGE_MESSAGES,
    )
    async def react_command(self, ctx: InteractionContext):
        message_id: str = ctx.kwargs['message'].strip()
        emoji: str = ctx.kwargs['emoji'].strip()
        partial_emoji = PartialEmoji.from_str(emoji)
        if partial_emoji is None:
            return await ctx.send('Unknown emoji!', ephemeral=True)
        guild = ctx.guild
        if guild is None:
            return await ctx.send('This must be used in a server!', ephemeral=True)
        await ctx.defer(ephemeral=True)
        message = await self.find_message(guild, message_id)
        if message is None:
            return await ctx.send('Message not found!', ephemeral=True)
        for reaction in message.reactions:
            if reaction.emoji == partial_emoji and reaction.me:
                await message.remove_reaction(partial_emoji)
                return await ctx.send('Removed reaction!', ephemeral=True)
        await message.add_reaction(partial_emoji)
        return await ctx.send('Added reaction!', ephemeral=True)

    @slash_command(
        'customreact',
        description='React to a message with a custom image',
        options=[
            SlashCommandOption(
                name='message',
                type=OptionType.STRING,
                description='The message to add the reaction to',
            ),
            SlashCommandOption(
                name='image',
                type=OptionType.ATTACHMENT,
                description='The image to react with',
            ),
            SlashCommandOption(
                name='name',
                type=OptionType.STRING,
                description='The name of the custom reaction',
                required=False,
            ),
        ],
    )
    async def customreact_command(self, ctx: InteractionContext):
        message_id: str = ctx.kwargs['message'].strip()
        image: Attachment = ctx.kwargs['image']
        name: str = ctx.kwargs.get('name', 'CustomEmoji')
        if (ctx.app_permissions & Permissions.MANAGE_EMOJIS_AND_STICKERS) == 0:
            return await ctx.send('I cannot add emojis... :(', ephemeral=True)
        if image.size >= 256 * 1024:
            return await ctx.send('File must not be larger than 256K!', ephemeral=True)
        guild = ctx.guild
        if guild is None:
            return await ctx.send('This must be used in a server!', ephemeral=True)
        await ctx.defer(ephemeral=True)
        message = await self.find_message(guild, message_id)
        if message is None:
            return await ctx.send('Message not found!', ephemeral=True)
        response = requests.get(image.url)
        file = BytesIO(response.content)
        try:
            emoji = await guild.create_custom_emoji(name, file, [], reason='Custom reaction')
            assert emoji is not None
        except HTTPException as e:
            self.bot.logger.error(f'HTTP Error: {await e.response.json()}')
            raise
        except:
            self.bot.logger.exception(f'Failed to create emoji in {guild.id}')
            return await ctx.send('Failed to create emoji!')
        await message.add_reaction(PartialEmoji(id=emoji.id))
        await emoji.delete(reason='Custom reaction')
        return await ctx.send('Custom reaction added!', ephemeral=True)


def setup(bot: CustomClient):
    ReactCommandExtension(bot)
