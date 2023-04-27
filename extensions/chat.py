import asyncio
import os
import time

import openai
from interactions import Extension, InteractionContext, Message, listen, slash_command
from interactions.api.events import MessageCreate
from openai.error import APIConnectionError

from client import CustomClient
from util import tomorrow

PROMPT = 'You are Quill, a concise and friendly language model.'
USER_LIMIT = 10000


async def create_chat_completion(**kwargs):
    for _ in range(5):
        try:
            return await openai.ChatCompletion.acreate(**kwargs)
        except APIConnectionError:
            await asyncio.sleep(0.2)


class ChatExtension(Extension):
    bot: CustomClient

    @slash_command('chat', description='Chat with OpenAI powered bot')
    async def chat(self, ctx: InteractionContext):
        # await ctx.send(
        #     'Hey, we got Clyde already. Don\'t waste my money! Do @Clyde to get started.'
        # )
        # return
        await ctx.defer()
        user_id = ctx.user.id
        user = self.bot.database.get_user(user_id)
        self.bot.logger.info(f'/chat user:{user_id}')
        if time.time() > user.chat_reset:
            user.chat_reset = tomorrow().timestamp()
            user.chat_used = 0
            self.bot.database.set_user(user_id, user)
        if user.chat_used > USER_LIMIT:
            await ctx.send(
                f'Sorry, you exceeded {USER_LIMIT} tokens today. Try again tomorrow!',
                ephemeral=True,
            )
            return
        chat: dict = await create_chat_completion(
            model='gpt-3.5-turbo',
            messages=[
                {'role': 'system', 'content': PROMPT},
                {'role': 'user', 'content': 'Hello!'},
            ],
        )  # type: ignore
        tokens: int = chat['usage']['total_tokens']
        user = self.bot.database.get_user(user_id)
        user.chat_used += tokens
        self.bot.database.set_user(user_id, user)
        await ctx.send(chat['choices'][0]['message']['content'])

    def chain(self, message: Message) -> list[dict]:
        # This message is sent by *a user* not *Quill*
        lst = []
        while True:
            self.bot.logger.debug(f'user message {message.id}: {message.content}')
            lst.append({'role': 'user', 'content': message.content})
            reply_to = message.get_referenced_message()
            if reply_to is None:
                return lst[::-1]
            assert reply_to.author.id == self.bot.user.id
            self.bot.logger.debug(
                f'assistant message {reply_to.id}: {reply_to.content}'
            )
            lst.append({'role': 'assistant', 'content': reply_to.content})
            user_message = reply_to.get_referenced_message()
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
            await message.channel.send(
                f'Sorry {message.author.mention}, you exceeded {USER_LIMIT} tokens '
                'today. Try again tomorrow!'
            )
            return
        self.bot.logger.debug(f'triggered message {message.id}: {message.content}')
        messages = self.chain(message)
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
    token = os.getenv('OPENAI_TOKEN')
    if token is None:
        bot.logger.warning('OPENAI_TOKEN env var not found, not enabling chat')
    else:
        openai.api_key = token
        ChatExtension(bot)
