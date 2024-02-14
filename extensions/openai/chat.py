import asyncio
import os
import time

import openai
from interactions import (
    Extension,
    InteractionContext,
    Message,
    listen,
    slash_command,
    SlashCommandOption,
    OptionType,
)
from interactions.api.events import MessageCreate
from openai.error import APIConnectionError, OpenAIError

from client import CustomClient
from util import tomorrow

PROMPT = 'You are Quill, a concise and friendly language model.'
USER_LIMIT = 10000


class ChatError(RuntimeError):
    pass


async def create_chat_completion(**kwargs):
    engine = os.getenv('AZURE_OPENAI_ENGINE')
    if engine:
        kwargs.setdefault('engine', engine)
    for _ in range(5):
        try:
            return await openai.ChatCompletion.acreate(**kwargs)
        except APIConnectionError:
            await asyncio.sleep(0.2)
        except OpenAIError as exc:
            if getattr(exc, 'code', None) == 'contentFilter':
                raise ChatError(exc.user_message)
            raise


class ChatExtension(Extension):
    bot: CustomClient

    @slash_command(
        'chat',
        description='Chat with GPT-3 bot',
        options=[
            SlashCommandOption(
                'message',
                type=OptionType.STRING,
                description='The initial message to send',
                required=False,
            )
        ],
    )
    async def chat(self, ctx: InteractionContext):
        # return await ctx.send(
        #     'Hey, we got Clyde already. Don\'t waste my money! Do @Clyde to get started.'
        # )
        message = ctx.kwargs.get('message', 'Hello!')
        user_id = ctx.user.id
        user = self.bot.database.get_user(user_id)
        self.bot.logger.info(f'/chat user:{user_id}')
        if time.time() > user.chat_reset:
            user.chat_reset = tomorrow().timestamp()
            user.chat_used = 0
            self.bot.database.set_user(user_id, user)
        if user.chat_used > USER_LIMIT:
            return await ctx.send(
                f'Sorry, you exceeded {USER_LIMIT} tokens today. Try again tomorrow!',
                ephemeral=True,
            )
        await ctx.defer()
        try:
            chat: dict = await create_chat_completion(
                model='gpt-3.5-turbo',
                messages=[
                    {'role': 'system', 'content': PROMPT},
                    {'role': 'user', 'content': message},
                ],
                user=f'quill-{user_id}',
            )  # type: ignore
        except ChatError as exc:
            return await ctx.send('**Error**: %s' % exc.args[0])
        tokens: int = chat['usage']['total_tokens']
        user = self.bot.database.get_user(user_id)
        user.chat_used += tokens
        self.bot.database.set_user(user_id, user)
        await ctx.send(chat['choices'][0]['message']['content'])

    async def chain(self, message: Message) -> list[dict]:
        # This message is sent by *a user* not *Quill*
        lst = []
        while True:
            self.bot.logger.debug(f'user message {message.id}: {message.content}')
            lst.append({'role': 'user', 'content': message.content})
            reply_to = await message.fetch_referenced_message()
            if reply_to is None:
                return lst[::-1]
            assert reply_to.author.id == self.bot.user.id
            self.bot.logger.debug(
                f'assistant message {reply_to.id}: {reply_to.content}'
            )
            lst.append({'role': 'assistant', 'content': reply_to.content})
            user_message = await reply_to.fetch_referenced_message()
            if user_message is None:
                return lst[::-1]
            message = user_message

    @listen()
    async def chat_response(self, event: MessageCreate):
        # return
        message = event.message
        if message.author.bot:
            return
        reply_to = message.get_referenced_message()
        if (
            reply_to is None
            or reply_to.author.id != self.bot.user.id
            or not reply_to.content
            or reply_to.embeds
            or reply_to.attachments
            or reply_to.components
        ):
            return
        user_id = message.author.id
        user = self.bot.database.get_user(user_id)
        if time.time() > user.chat_reset:
            user.chat_reset = tomorrow().timestamp()
            user.chat_used = 0
            self.bot.database.set_user(user_id, user)
        if user.chat_used > USER_LIMIT:
            return await message.channel.send(
                f'Sorry {message.author.mention}, you exceeded {USER_LIMIT} tokens '
                'today. Try again tomorrow!'
            )
        self.bot.logger.debug(f'triggered message {message.id}: {message.content}')
        messages = await self.chain(message)
        chat: dict = await create_chat_completion(
            model='gpt-3.5-turbo',
            messages=[{'role': 'system', 'content': PROMPT}] + messages,
            user=f'quill-{message.author.id}',
        )  # type: ignore
        tokens: int = chat['usage']['total_tokens']
        user = self.bot.database.get_user(user_id)
        user.chat_used += tokens
        self.bot.database.set_user(user_id, user)
        await message.reply(chat['choices'][0]['message']['content'])


def setup(bot: CustomClient):
    if openai.api_key:
        ChatExtension(bot)
    else:
        bot.logger.warning('openai.api_key not found, not enabling chat')
