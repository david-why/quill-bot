from typing import cast

from interactions import (
    CommandType,
    ContextMenuContext,
    Embed,
    Extension,
    InputText,
    Member,
    Message,
    Modal,
    ModalContext,
    Permissions,
    TextStyles,
    context_menu,
    modal_callback,
)

from client import CustomClient


class EditContextExtension(Extension):
    bot: CustomClient

    @context_menu(
        'Edit message',
        context_type=CommandType.MESSAGE,
        default_member_permissions=Permissions.MANAGE_MESSAGES,
        dm_permission=False,
    )
    async def edit_context(self, ctx: ContextMenuContext):
        message = cast(Message, ctx.target)
        author = message.author
        if isinstance(author, Member):
            author = author.user
        if author.id != self.bot.user.id:
            return await ctx.send('I cannot edit a message not my own!', ephemeral=True)
        modal = Modal(title='Edit this message', custom_id='edit_modal')
        mid = str(message.id)
        message_id = InputText(
            label=f'Message ID (DO NOT EDIT)',
            style=TextStyles.SHORT,
            custom_id='message_id',
            value=mid,
            min_length=len(mid),
            max_length=len(mid),
        )
        content = InputText(
            label='Text content (not in embed)',
            style=TextStyles.PARAGRAPH,
            custom_id='content',
            value=message.content or '',
            required=False,
        )
        embed = message.embeds[0] if message.embeds else Embed()
        title = InputText(
            label='Embed title (leave blank to DELETE embed)',
            style=TextStyles.SHORT,
            custom_id='title',
            value=embed.title or '',
            required=False,
        )
        body = InputText(
            label='Embed content (inside the embed)',
            style=TextStyles.PARAGRAPH,
            custom_id='body',
            value=embed.description or '',
            required=False,
        )
        modal.add_components(message_id, content, title, body)
        await ctx.send_modal(modal)

    @modal_callback('edit_modal')
    async def edit_modal_callback(
        self,
        ctx: ModalContext,
        *,
        message_id: str,
        content: str,
        title: str,
        body: str,
        **kwargs,
    ):
        if kwargs:
            self.bot.logger.warn(f'Received unexpected kwargs for edit: {kwargs}')
        if not message_id.isdigit():
            return await ctx.send(
                'I told you not to edit the Message ID, heh?', ephemeral=True
            )
        message = await ctx.channel.fetch_message(message_id)
        if message is None:
            return await ctx.send(
                'Message not found! Either you changed the Message ID, or '
                'the message was deleted.',
                ephemeral=True,
            )
        if not title:
            embed = None
        else:
            embed = message.embeds[0] if message.embeds else Embed()
            embed.title = title
            embed.description = body
        await message.edit(content=content or None, embeds=embed)
        return await ctx.send('Message edited!', ephemeral=True)


def setup(bot: CustomClient):
    EditContextExtension(bot)
