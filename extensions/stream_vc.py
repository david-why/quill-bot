import youtube_dl
from interactions import (
    TYPE_VOICE_CHANNEL,
    ChannelType,
    Extension,
    InteractionContext,
    OptionType,
    SlashCommandOption,
    slash_command,
)
from interactions.api.voice.audio import Audio
from client import CustomClient

DESC = 'Stream some audio in VC'


class StreamCommandExtension(Extension):
    bot: CustomClient

    def __init__(self, bot):
        super().__init__()
        self._state = None

    @slash_command(
        'stream',
        description=DESC,
        sub_cmd_name='youtube',
        sub_cmd_description='Stream a YouTube video in VC (audio-only)',
        dm_permission=False,
        options=[
            SlashCommandOption(
                name='channel',
                type=OptionType.CHANNEL,
                description='VC to stream the audio in',
                channel_types=[ChannelType.GUILD_VOICE, ChannelType.GUILD_STAGE_VOICE],
            ),
            SlashCommandOption(
                name='url',
                type=OptionType.STRING,
                description='YouTube link to stream',
            ),
        ],
    )
    async def stream_youtube_command(self, ctx: InteractionContext):
        channel: TYPE_VOICE_CHANNEL = ctx.kwargs['channel']
        url: str = ctx.kwargs['url']
        message = await ctx.send('Fetching information from YouTube...')
        with youtube_dl.YoutubeDL() as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as exc:
                self.bot.logger.exception(f'Fetch YT url {url!r} error!')
                return await message.edit(
                    content=f'Error fetching URL information! {exc}'
                )
        if info is None:
            return await message.edit(content='No information found for the URL!')
        fmt = None
        for f in info['formats']:
            if f.get('vcodec') == 'none':
                fmt = f
                break
        if fmt is None:
            for f in info['formats']:
                if f.get('acodec') != 'none':
                    fmt = f
                    break
        if fmt is None:
            return await message.edit(content='No audio format found for the URL!')
        self._state = state = await channel.connect()
        if not state.connected:
            return await message.edit(
                content=f'I cannot connect to channel {channel.mention}!'
            )
        if state.mute:
            return await message.edit(
                content=f'I cannot speak in channel {channel.mention}!'
            )
        await message.edit(content=f'Playing **<{url}>**!')
        await state.play(Audio(fmt['url']))
        await state.disconnect()
        self._state = None

    @slash_command(
        'stream',
        description=DESC,
        sub_cmd_name='stop',
        sub_cmd_description='Stop streaming audio in VC',
        dm_permission=False,
    )
    async def stream_stop_command(self, ctx: InteractionContext):
        if self._state is None:
            return await ctx.send('Not connected to VC!')
        state = self._state
        self._state = None
        if state.player:
            state.player.stop()
        mention = state.channel.mention
        # await state.disconnect()
        await ctx.send(f'Stopped playing in {mention}!')


def setup(bot: CustomClient):
    StreamCommandExtension(bot)
