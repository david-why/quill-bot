import asyncio
import os
import time

import openai
from interactions import (
    Embed,
    EmbedAttachment,
    Extension,
    InteractionContext,
    OptionType,
    SlashCommandOption,
    slash_command,
)
from openai.error import APIConnectionError

from client import CustomClient
from util import tomorrow

USER_LIMIT = 5


async def create_image(**kwargs):
    for _ in range(5):
        try:
            return await openai.Image.acreate(**kwargs)
        except APIConnectionError:
            await asyncio.sleep(0.2)


class ImagegenCommandExtension(Extension):
    bot: CustomClient

    @slash_command(
        'imagegen',
        description='Generate an image based on a text prompt',
        options=[
            SlashCommandOption(
                name='prompt',
                type=OptionType.STRING,
                description='The prompt of image generation',
            )
        ],
    )
    async def imagegen_command(self, ctx: InteractionContext):
        args = ctx.kwargs
        prompt: str = args['prompt']
        user_id = ctx.user.id
        user = self.bot.database.get_user(user_id)
        if time.time() > user.images_reset:
            user.images_reset = tomorrow().timestamp()
            user.images_used = 0
            self.bot.database.set_user(user_id, user)
        if user.images_used > USER_LIMIT:
            await ctx.send(
                f'Sorry, you exceeded {USER_LIMIT} images today. Try again tomorrow!',
                ephemeral=True,
            )
            return
        await ctx.defer()
        image: dict = await create_image(prompt=prompt, n=1, size='512x512')  # type: ignore
        image_url: str = image['data'][0]['url']
        print(image_url)
        user = self.bot.database.get_user(user_id)
        user.images_used += 1
        self.bot.database.set_user(user_id, user)
        embed = Embed(images=[EmbedAttachment(image_url)])
        await ctx.send('Here is the generated image!', embeds=embed)
        # await ctx.send('Work In Progress', ephemeral=True)


def setup(bot: CustomClient):
    token = os.getenv('OPENAI_TOKEN')
    if token is None:
        bot.logger.warning('OPENAI_TOKEN env var not found, not enabling imagegen')
    else:
        openai.api_key = token
        ImagegenCommandExtension(bot)
