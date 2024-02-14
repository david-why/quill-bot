import time

import openai
from interactions import Embed, EmbedField, Extension, InteractionContext, slash_command

from client import CustomClient
from util import tomorrow

CHAT_LIMIT = 10000
IMAGE_LIMIT = 5


class InfoCommandExtension(Extension):
    bot: CustomClient

    @slash_command('info', description='Show info on number of tokens used')
    async def info_command(self, ctx: InteractionContext):
        user_id = ctx.user.id
        self.bot.logger.info(f'/info user:{user_id}')
        user = self.bot.database.get_user(user_id)
        if time.time() > user.chat_reset:
            user.chat_reset = tomorrow().timestamp()
            user.chat_used = 0
            self.bot.database.set_user(user_id, user)
        if time.time() > user.images_reset:
            user.images_reset = tomorrow().timestamp()
            user.images_used = 0
            self.bot.database.set_user(user_id, user)
        fields = []
        if openai.api_key:
            fields.extend(
                [
                    EmbedField(
                        '/chat tokens',
                        f'You have used {user.chat_used} of {CHAT_LIMIT} tokens today.\n'
                        'Each 1,000 words are approximately worth 750 tokens; however, '
                        'note that ALL chat context (all text in the chain of replies) '
                        'also counts as tokens, so start a new chat to save on tokens!',
                    ),
                    EmbedField(
                        '/imagegen images',
                        f'You have generated {user.images_used} of {IMAGE_LIMIT} '
                        'images today.\n',
                    ),
                ]
            )
        embed = Embed(
            title='Quill User Info',
            description='Here is all the information for you in the Quill bot.',
            fields=fields,
        )
        await ctx.send(embeds=embed, ephemeral=True)


def setup(bot: CustomClient):
    InfoCommandExtension(bot)
