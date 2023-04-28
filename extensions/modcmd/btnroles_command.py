import time
from typing import Dict, List, Optional, Tuple, cast

from interactions import (
    TYPE_MESSAGEABLE_CHANNEL,
    ActionRow,
    Button,
    ButtonStyle,
    ChannelSelectMenu,
    ChannelType,
    ComponentContext,
    Embed,
    EmbedFooter,
    Extension,
    Guild,
    InteractionContext,
    Message,
    OptionType,
    Permissions,
    Role,
    RoleSelectMenu,
    SlashCommandOption,
    Snowflake_Type,
    component_callback,
    listen,
    slash_command,
)
from interactions.api.events import Component, MessageCreate
from interactions.client.errors import HTTPException

from client import CustomClient

DESC = 'Create message that grant roles automatically when a button is clicked'

split_rows = ActionRow.split_components


class Pending:
    def __init__(self, message: Message):
        self.message = message
        self.stage = 1
        self.title = None
        self.content = None
        self.roles: List[Tuple[int, str]] = []
        self.pending_role = None
        self.last_update = time.time()

    def add_title(self, title: str):
        self.title = title
        self.stage = 2
        self.last_update = time.time()

    def add_content(self, content: str):
        self.content = content
        self.stage = 3
        self.last_update = time.time()

    def add_channel(self, channel_id: int):
        self.channel_id = channel_id
        self.stage = 4
        self.last_update = time.time()

    def has_role(self, role_id: int):
        for role in self.roles:
            if role[0] == role_id:
                return True
        return self.pending_role == role_id

    def add_role(self, role_id: int):
        self.pending_role = role_id
        self.last_update = time.time()

    def add_role_text(self, text: str):
        if self.pending_role is not None:
            role = self.pending_role
            self.roles.append((role, text))
            self.pending_role = None


class ButtonRolesCommandExtension(Extension):
    bot: CustomClient

    def __init__(self, _) -> None:
        self.pending: Dict[Tuple[int, int], Pending] = {}

    async def _prune(self, keep=None):
        threshold = time.time() - 60 * 10
        for (user_id, channel_id), pending in list(self.pending.items()):
            if pending is keep:
                continue
            if pending.last_update <= threshold:
                channel = await self.bot.fetch_channel(channel_id)
                user = await self.bot.fetch_user(user_id)
                assert user and isinstance(channel, TYPE_MESSAGEABLE_CHANNEL)
                await channel.send(f'{user.mention}: Your btnroles timed out!')
                del self.pending[(user_id, channel_id)]

    @slash_command(
        'btnroles',
        description=DESC,
        default_member_permissions=Permissions.MANAGE_ROLES,
        sub_cmd_name='setup',
        sub_cmd_description='Create a button roles message interactively',
    )
    async def roles_setup_command(self, ctx: InteractionContext):
        guild = ctx.guild
        if guild is None:
            return await ctx.send('This can only be used in a server!', ephemeral=True)
        bot_member = await self.bot.fetch_member(self.bot.user.id, guild.id)
        assert bot_member is not None
        if not bot_member.has_permission(Permissions.MANAGE_ROLES):
            return await ctx.send('I do not have the Manage Roles permission... :(')
        await self._prune()
        user_id = ctx.user.id
        channel_id = ctx.channel_id
        embed = Embed(
            title='Button Roles Setup',
            description='Let\'s add a button roles message!\n'
            'What do you want the title to say?\n'
            '(Just type it in the chat!)',
            footer=EmbedFooter('Step 1 of 4'),
        )
        message = await ctx.send(embeds=embed)
        pending = Pending(message)
        self.pending[(user_id, channel_id)] = pending

    @listen()
    async def on_new_message(self, event: MessageCreate):
        message = event.message
        user_id = message.author.id
        channel = message.channel
        channel_id = channel.id
        pending = self.pending.get((user_id, channel_id))
        if pending is None:
            return
        if message == 'cancel':
            del self.pending[(user_id, channel_id)]
            return await message.reply('OK, canceled setup!')
        await self._prune(pending)
        if pending.stage == 1:
            title = message.content
            pending.add_title(title)
            embed = Embed(
                title='Button Roles Setup',
                description='OK, nice! Now, what is the main content?\n'
                '(Type "none" without quotation marks for no content)',
                footer=EmbedFooter('Step 2 of 4'),
            )
            preview = Embed(title=title)
            await message.reply(embeds=[embed, preview])
        elif pending.stage == 2:
            content = message.content
            if content == 'none':
                content = ''
            pending.add_content(content)
            embed = Embed(
                title='Button Roles Setup',
                description='Amazing! Now I need to know where to send the message.\n'
                'Please choose a channel below!',
                footer=EmbedFooter('Step 3 of 4'),
            )
            preview = Embed(title=pending.title, description=content)
            select = ChannelSelectMenu(
                channel_types=[ChannelType.GUILD_TEXT], custom_id='btnroles_stage3'
            )
            await message.reply(
                embeds=[embed, preview],
                components=[select],  # type: ignore
            )
        elif pending.stage == 4:
            if pending.pending_role is None:
                return
            text = message.content
            pending.add_role_text(text)
            if len(pending.roles) >= 23:
                await message.reply(
                    'Oops, you reached the maximum number of roles. '
                    'Sending the roles message now!'
                )
                return await self.send_roles(
                    message.guild.fetch_channel(pending.channel_id),  # type: ignore
                    pending,
                )
            embed = Embed(
                title='Button Roles Setup',
                description='Got that role! What\'s next?',
                footer=EmbedFooter('Step 4 of 4'),
            )
            preview = Embed(title=pending.title, description=pending.content)
            components = []
            for _, text in pending.roles:
                components.append(
                    Button(style=ButtonStyle.SECONDARY, label=text, disabled=True)
                )
            select = RoleSelectMenu(custom_id='btnroles_stage4')
            end = Button(
                style=ButtonStyle.SECONDARY,
                label='Done!',
                custom_id='btnroles_stage4_end',
            )
            await message.reply(
                embeds=[embed, preview],
                components=[
                    *split_rows(*components),
                    ActionRow(select),
                    ActionRow(end),
                ],  # type: ignore
            )
        else:
            return

    @component_callback('btnroles_stage3')
    async def btnroles_stage3_callback(self, ctx: ComponentContext):
        message = ctx.message
        assert message
        user_id = ctx.user.id
        channel = message.channel
        channel_id = channel.id
        pending = self.pending.get((user_id, channel_id))
        if pending is None:
            return await ctx.send('Please don\'t do that again...', ephemeral=True)
        send_channel: TYPE_MESSAGEABLE_CHANNEL = ctx.values[0]  # type: ignore
        pending.add_channel(send_channel.id)
        embed = Embed(
            title='Button Roles Setup',
            description='Great! Lastly, we need to add roles.\n'
            'What is a role you want to add?\n'
            '(Or click "Done!" to finish!)',
            footer=EmbedFooter('Step 4 of 4'),
        )
        preview = Embed(title=pending.title, description=pending.content)
        select = RoleSelectMenu(custom_id='btnroles_stage4')
        end = Button(
            style=ButtonStyle.SECONDARY, label='Done!', custom_id='btnroles_stage4_end'
        )
        await ctx.send(embeds=[embed, preview], components=[[select], [end]])

    @component_callback('btnroles_stage4')
    async def btnroles_stage4_callback(self, ctx: ComponentContext):
        user_id = ctx.user.id
        channel_id = ctx.channel_id
        pending = self.pending.get((user_id, channel_id))
        if pending is None:
            return await ctx.send('Please don\'t do that again...', ephemeral=True)
        role: Role = ctx.values[0]  # type: ignore
        role_id = role.id
        if pending.has_role(role_id):
            await ctx.send('That role is already added. Try another one!')
            return
        pending.add_role(role_id)
        await ctx.send(f'OK, now send the label for the {role.mention} button!')

    async def send_roles(self, channel: TYPE_MESSAGEABLE_CHANNEL, pending: Pending):
        embed = Embed(title=pending.title, description=pending.content)
        roles = []
        for role_id, text in pending.roles:
            roles.append(
                Button(
                    style=ButtonStyle.SECONDARY,
                    label=text,
                    custom_id=f'br_@{role_id}',
                )
            )
        return await channel.send(embeds=embed, components=split_rows(*roles))

    @component_callback('btnroles_stage4_end')
    async def btnroles_stage4_end_callback(self, ctx: ComponentContext):
        user_id = ctx.user.id
        channel_id = ctx.channel_id
        pending = self.pending.get((user_id, channel_id))
        if pending is None:
            return await ctx.send('Please don\'t do that again...', ephemeral=True)
        del self.pending[(user_id, channel_id)]
        send_channel = await self.bot.fetch_channel(pending.channel_id)
        if not isinstance(send_channel, TYPE_MESSAGEABLE_CHANNEL):
            return await ctx.send('ERORR: Channel not messageable!')
        await self.send_roles(send_channel, pending)
        await ctx.send('Success! Check out the message now!')

    @listen()
    async def on_roles_component(self, event: Component):
        ctx = event.ctx
        if not ctx.custom_id.startswith('br_@'):
            return
        role_id = int(ctx.custom_id[4:])
        member = ctx.member
        if member is None:
            self.bot.logger.warn(f'Member is None for {ctx.custom_id}!')
            return
        func = member.add_role
        is_removing = member.has_role(role_id)
        if is_removing:
            func = member.remove_role
        try:
            await func(role_id)
        except HTTPException as exc:
            if exc.code == 50013:
                return await ctx.send(
                    'I can\'t change this role for you. Please ask the server admins '
                    'if I have the Manage Roles permission AND I have a role higher '
                    'than the one you are trying to get in the Roles list.',
                    ephemeral=True,
                )
            raise
        action = 'removed' if is_removing else 'added'
        await ctx.send(f'Role <@&{role_id}> {action}!', ephemeral=True)

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
        'btnroles',
        description=DESC,
        default_member_permissions=Permissions.MANAGE_ROLES,
        sub_cmd_name='add',
        sub_cmd_description='Add a role to a created message',
        options=[
            SlashCommandOption(
                name='message',
                type=OptionType.STRING,
                description='The message ID to update',
            ),
            SlashCommandOption(
                name='role',
                type=OptionType.ROLE,
                description='The role to add',
            ),
            SlashCommandOption(
                name='label',
                type=OptionType.STRING,
                description='The label on the button',
            ),
        ],
    )
    async def roles_add_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        message_id: str = args['message']
        role: Role = args['role']
        label: str = args['label']
        guild = ctx.guild
        if guild is None:
            return await ctx.send(
                'You can only use this command in a server!', ephemeral=True
            )
        await ctx.defer(ephemeral=True)
        message = await self.find_message(guild, message_id)
        if message is None:
            return await ctx.send(
                'The message is not found; please double check the message ID!'
            )
        if not message.embeds:
            return await ctx.send('The message doesn\'t have an embed, did I send it?')
        embed = message.embeds[0]
        rows = message.components or []
        components = cast(List[Button], [c for row in rows for c in row.components])
        components.append(
            Button(style=ButtonStyle.SECONDARY, label=label, custom_id=f'br_@{role.id}')
        )
        await message.edit(embeds=embed, components=split_rows(*components))
        await ctx.send('Edited message!')

    @slash_command(
        'btnroles',
        description=DESC,
        default_member_permissions=Permissions.MANAGE_ROLES,
        sub_cmd_name='edit',
        sub_cmd_description='Edits a created message',
        options=[
            SlashCommandOption(
                name='message',
                type=OptionType.STRING,
                description='The message ID to update',
            ),
            SlashCommandOption(
                name='title',
                type=OptionType.STRING,
                description='The new title',
                required=False,
            ),
            SlashCommandOption(
                name='content',
                type=OptionType.STRING,
                description='The new body content (Use \\n for newline)',
                required=False,
            ),
        ],
    )
    async def roles_edit_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        message_id: str = args['message']
        title: Optional[str] = args.get('title')
        content: Optional[str] = args.get('content')
        if title is None and content is None:
            return await ctx.send('Nothing to update!', ephemeral=True)
        guild = ctx.guild
        if guild is None:
            return await ctx.send(
                'You can only use this command in a server!', ephemeral=True
            )
        await ctx.defer(ephemeral=True)
        message = await self.find_message(guild, message_id)
        if message is None:
            return await ctx.send(
                'The message is not found; please double check the message ID!'
            )
        if not message.embeds:
            return await ctx.send('The message doesn\'t have an embed, did I send it?')
        embed = message.embeds[0]
        components = message.components
        if title is not None:
            embed.title = title
        if content is not None:
            embed.description = content.replace('\\n', '\n').replace('\\\\', '\\')
        await message.edit(embeds=embed, components=components)
        await ctx.send('Edited message!')

    @slash_command(
        'btnroles',
        description=DESC,
        default_member_permissions=Permissions.MANAGE_ROLES,
        sub_cmd_name='editrole',
        sub_cmd_description='Edits a role on a created message',
        options=[
            SlashCommandOption(
                name='message',
                type=OptionType.STRING,
                description='The message ID to update',
            ),
            SlashCommandOption(
                name='index',
                type=OptionType.INTEGER,
                description='The index of the role to edit, 1-based',
                min_value=1,
            ),
            SlashCommandOption(
                name='role',
                type=OptionType.ROLE,
                description='The new role to replace with',
                required=False,
            ),
            SlashCommandOption(
                name='label',
                type=OptionType.STRING,
                description='The new label of the role',
                required=False,
            ),
            SlashCommandOption(
                name='delete',
                type=OptionType.BOOLEAN,
                description='Delete this role',
                required=False,
            ),
        ],
    )
    async def roles_editrole_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        message_id: str = args['message']
        index: int = args['index']
        role: Optional[Role] = args.get('role')
        label: Optional[str] = args.get('label')
        delete: bool = args.get('delete', False)
        if role is None and label is None and not delete:
            return await ctx.send('Nothing to update!', ephemeral=True)
        guild = ctx.guild
        if guild is None:
            return await ctx.send(
                'You can only use this command in a server!', ephemeral=True
            )
        await ctx.defer(ephemeral=True)
        message = await self.find_message(guild, message_id)
        if message is None:
            return await ctx.send(
                'The message is not found; please double check the message ID!'
            )
        if not message.embeds:
            return await ctx.send('The message doesn\'t have an embed, did I send it?')
        embed = message.embeds[0]
        rows = message.components or []
        components = cast(List[Button], [c for row in rows for c in row.components])
        if index > len(components):
            return await ctx.send('The specified index is a little too big!')
        if delete:
            components.pop(index - 1)
        else:
            if role is not None:
                for i, component in enumerate(components):
                    if i != index - 1 and component.custom_id == f'br_@{role.id}':
                        return await ctx.send(
                            'The role is already somewhere in the message!'
                        )
                components[index - 1].custom_id = f'br_@{role.id}'
            if label is not None:
                components[index - 1].label = label
        await message.edit(embeds=embed, components=split_rows(*components))
        await ctx.send('Edited message!')


def setup(bot: CustomClient):
    ButtonRolesCommandExtension(bot)
