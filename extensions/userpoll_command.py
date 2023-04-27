from interactions import (
    ComponentContext,
    Embed,
    EmbedFooter,
    Extension,
    InteractionContext,
    OptionType,
    SlashCommandOption,
    User,
    UserSelectMenu,
    component_callback,
    slash_command,
)

from client import CustomClient
from util import error_embed


class UserpollCommandExtension(Extension):
    bot: CustomClient

    @slash_command(
        'userpoll',
        description='Create a poll for users',
        options=[
            SlashCommandOption(
                name='text',
                type=OptionType.STRING,
                description='The text to display with the poll',
            ),
            SlashCommandOption(
                name='min',
                type=OptionType.INTEGER,
                description='Minimum number of users to select',
                required=False,
                min_value=1,
                max_value=25,
            ),
            SlashCommandOption(
                name='max',
                type=OptionType.INTEGER,
                description='Maximum number of users to select',
                required=False,
                min_value=1,
                max_value=25,
            ),
        ],
    )
    async def userpoll_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        text: str = args['text']
        min_values: int = args.get('min', 1)
        max_values: int = args.get('max', 1)
        select = UserSelectMenu(
            placeholder='Choose a user',
            min_values=min_values,
            max_values=max_values,
            custom_id='userpoll_select',
        )
        embed = Embed(
            title='Poll results',
            description='No results yet!',
            footer=EmbedFooter('Voted: N/A'),
        )
        await ctx.send(text, embeds=embed, components=select)

    @component_callback('userpoll_select')
    async def userpoll_select_callback(self, ctx: ComponentContext):
        message = ctx.message
        if message is None:
            await ctx.send(embeds=error_embed('Unknown error -17'), ephemeral=True)
            return
        responder = ctx.user
        embed = message.embeds[0]
        desc = embed.description
        if desc is None or desc == 'No results yet!':
            desc = ''
        footer = embed.footer
        assert footer is not None
        if responder.mention in footer.text:
            await ctx.send('You have already responded to this poll!', ephemeral=True)
            return
        if footer.text == 'Voted: N/A':
            footer.text = f'Voted: {responder.mention}'
        else:
            footer.text += f', {responder.mention}'
        embed.footer = footer
        lines = desc.splitlines()
        users: list[User] = ctx.values  # type: ignore
        for user in users:
            mention = user.mention
            for i, line in enumerate(lines):
                if line.startswith(f'{mention}: '):
                    count = int(line.partition(': ')[2]) + 1
                    lines[i] = f'{mention}: {count}'
                    break
            else:
                lines.append(f'{mention}: 1')
        embed.description = '\n'.join(lines)
        await ctx.edit_origin(embeds=embed)


def setup(bot: CustomClient):
    UserpollCommandExtension(bot)
