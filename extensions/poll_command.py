from interactions import (
    Extension,
    InteractionContext,
    slash_command,
    Button,
    ButtonStyle,
    ActionRow,
    SlashCommandOption,
    OptionType,
    component_callback,
    ComponentContext,
)
from typing import List

from client import CustomClient


class PollCommandExtension(Extension):
    bot: CustomClient

    @slash_command(
        'poll',
        description='Create a poll',
        options=[
            SlashCommandOption(
                'question',
                type=OptionType.STRING,
                description='The question to ask everyone',
            ),
            SlashCommandOption(
                'options',
                type=OptionType.STRING,
                description='The options, separated by a pipe character (|)',
            ),
        ],
    )
    async def poll_command(self, ctx: InteractionContext):
        question: str = ctx.kwargs['question']
        options: List[str] = ctx.kwargs['options'].split('|')
        if len(options) > 25:
            return await ctx.send('Cannot send more than 25 options!', ephemeral=True)
        components = []
        content = '%s\n' % question
        for i, option in enumerate(options):
            components.append(
                Button(
                    style=ButtonStyle.SECONDARY,
                    label=option,
                    custom_id='poll_%d' % i,
                )
            )
            content += '%d. %s `(Voters: 0)`\n' % (i + 1, option)
        return await ctx.send(
            content.strip(), components=ActionRow.split_components(*components)
        )

    @component_callback(*('poll_%d' % i for i in range(25)))
    async def poll_component_callback(self, ctx: ComponentContext):
        index = int(ctx.custom_id[5:])
        message_id = ctx.message_id
        guild_id = ctx.guild_id
        channel_id = ctx.channel_id
        user_id = ctx.user.id
        if self.bot.database.has_poll(message_id, guild_id, channel_id, user_id):
            return await ctx.send('You already voted on the poll!', ephemeral=True)
        self.bot.database.add_poll(message_id, guild_id, channel_id, user_id)
        message = await ctx.channel.fetch_message(message_id)
        assert message
        lines = message.content.splitlines()
        line = lines[index + 1]
        option, _, count = line.rpartition(' `(Voters: ')
        lines[index + 1] = '%s `(Voters: %d)`' % (option, int(count[:-2]) + 1)
        content = '\n'.join(lines)
        await ctx.edit_origin(content=content)


def setup(bot: CustomClient):
    PollCommandExtension(bot)
