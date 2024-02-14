import asyncio
import io
import time
from typing import cast

import openai
import requests
from interactions import (
    Extension,
    File,
    InteractionContext,
    OptionType,
    SlashCommandOption,
    slash_command,
)
from openai.error import APIConnectionError, InvalidRequestError, OpenAIError

from client import CustomClient
from util import tomorrow

USER_LIMIT = 5


class ImagegenError(RuntimeError):
    pass


async def create_image(**kwargs):
    for _ in range(5):
        try:
            return await openai.Image.acreate(**kwargs)
        except APIConnectionError:
            await asyncio.sleep(0.2)
        except OpenAIError as exc:
            if getattr(exc, 'code', None) == 'contentFilter':
                raise ImagegenError(exc.user_message)
            raise


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
            return await ctx.send(
                f'Sorry, you exceeded {USER_LIMIT} images today. Try again tomorrow!',
                ephemeral=True,
            )
        await ctx.defer()
        try:
            image = cast(dict, await create_image(prompt=prompt, n=1, size='512x512'))
        except ImagegenError as exc:
            return await ctx.send('**Error**: %s' % exc.args[0])
        image_url: str = image['data'][0]['url']
        print(image_url)
        user = self.bot.database.get_user(user_id)
        user.images_used += 1
        self.bot.database.set_user(user_id, user)
        r = requests.get(image_url)
        buf = io.BytesIO(r.content)
        await ctx.send(f'Here is the generated image!', files=File(buf, 'image.png'))


def setup(bot: CustomClient):
    if openai.api_key:
        ImagegenCommandExtension(bot)
    else:
        bot.logger.warning('openai.api_key not found, not enabling imagegen')
