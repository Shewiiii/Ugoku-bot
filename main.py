import discord
import yt_dlp
import asyncio

import urllib
import re
import logging
import os
from dotenv import load_dotenv
from bot.line import get_stickerpack
from bot.downloader import *
from bot.exceptions import *
from bot.settings import *
from bot.arls import *
from bot.timer import Timer

# From https://gist.github.com/aliencaocao/83690711ef4b6cec600f9a0d81f710e5
yt_dlp.utils.bug_reports_message = lambda: ''  # disable yt_dlp bug report
ytdl_format_options: dict[str, Any] = {
    'format': 'bestaudio',
    'outtmpl': 'output/videos/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'no-playlist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'geo-bypass': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'no_color': True,
    'overwrites': True,
    'age_limit': 100,
    'live_from_start': True,
    'cookiesfrombrowser': ('firefox',)
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
ffmpeg_options = {'options': '-vn -sn'}


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


load_dotenv()
bot = discord.Bot()
TOKEN = os.getenv('DISCORD_TOKEN')
DEV_TOKEN = os.getenv('DEV_TOKEN')
ARL = os.getenv('DEEZER_ARL')

vc_config_path = Path('.') / 'deemix' / 'vc_config'

# VC deemix settings: ignore tags and download only the song itself
# Init settings
vc_settings = loadSettings(vc_config_path)


@bot.command(name="ping", description='Test the reactivity of Ugoku !')
async def ping(ctx) -> None:
    latency = round(bot.latency*1000, 2)
    logging.info(f'Pinged latency: {latency}')
    await ctx.respond(f'あわあわあわわわ ! {latency}ms')


get = bot.create_group(
    "get",
    "Get stuff from Ugoku !"
)


@get.command(
    name='stickers',
    description='Download a LINE sticker pack from a given URL.',
)
@discord.option(
    'url',
    type=discord.SlashCommandOptionType.string,
    description='URL of a sticker pack from LINE Store.',
)
@discord.option(
    'gif',
    type=discord.SlashCommandOptionType.boolean,
    description=('Convert animated png to gifs, more widely supported. '
                 'Default: True.'),
    autocomplete=discord.utils.basic_autocomplete(
        [True, False]),
)
async def stickers(
    ctx: discord.ApplicationContext,
    url: int | None = None,
    gif: bool = True,
) -> None:
    timer = Timer()

    if not id and not url:
        await ctx.respond(f'Please specify a URL or a sticker pack ID.')
    else:
        await ctx.respond(f'Give me a second !')
        zip_file = get_stickerpack(url, gif=gif)
        await ctx.send(
            file=discord.File(zip_file),
            content=(f"Sorry for the wait <@{ctx.author.id}> ! "
                     "Here's the sticker pack you requested.")
        )
        await ctx.edit(content=f'Done ! {timer.total()}')


@get.command(
    name='songs',
    description='Download your favorite songs !',
)
@discord.option(
    'url',
    type=discord.SlashCommandOptionType.string,
    description='Spotify/Deezer URL of a song, an album or a playlist. Separate urls with semi-colons.',
)
@discord.option(
    'format',
    type=discord.SlashCommandOptionType.string,
    description='The format of the files you want to save.',
    autocomplete=discord.utils.basic_autocomplete(
        ['FLAC', 'MP3 320', 'MP3 128']),
)
async def songs(
    ctx: discord.ApplicationContext,
    url,
    format: str | int | None = None,
) -> None:
    timer = Timer()

    await ctx.respond(f'Give me a second !')
    arl = get_setting(
        ctx.author.id,
        'publicArl',
        ARL
    )

    if not format:
        format = get_setting(
            ctx.user.id,
            'defaultMusicFormat',
            'MP3 320'
        )
    try:
        downloadObjects, format_ = init_dl(
            url=url,
            user_id=ctx.user.id,
            arl=arl,
            brfm=format
        )
        if not downloadObjects:
            raise TrackNotFound

        await ctx.edit(
            content=f'Download objects got, {timer.round()}. '
            'Fetching track data...'
        )
        results = await download(
            downloadObjects,
            format_,
            ctx=ctx,
            arl=arl,
            timer=timer,
        )
        path = results['path']

        size = os.path.getsize(path)
        ext = os.path.splitext(path)[1][1:]
        # To check if the Deezer account is paid (?)
        if 'zip' != ext and ext not in format.lower():
            raise InvalidARL

        logging.info(f'Chosen format: {format}')
        logging.info(f'File size: {size}, Path: {path}')

        if size >= ctx.guild.filesize_limit:
            if format != 'MP3 320' and format != 'MP3 128':

                await ctx.edit(
                    content='Track too heavy, trying '
                            'to download with MP3 320...'
                )
                downloadObjects, format_ = init_dl(
                    url=url,
                    user_id=ctx.user.id,
                    arl=arl,
                    brfm='mp3 320'
                )
                results = await download(
                    downloadObjects,
                    format_=format_,
                    ctx=ctx,
                    arl=arl,
                    timer=timer,
                )

                path = results['path']
                size = os.path.getsize(path)
                logging.info(f'File size: {size}, Path: {path}')
                if size >= ctx.guild.filesize_limit:
                    await ctx.edit(content='Track too heavy ￣へ￣')
                    return
            else:
                await ctx.edit(content='Track too heavy ￣へ￣')
                return
        # SUCESS:
        await ctx.edit(
            content=f'Download finished, {timer.round()}. Uploading...'
        )
        await ctx.send(
            file=discord.File(path),
            content=(f"Sorry for the wait <@{ctx.author.id}> ! "
                     "Here's the song(s) you requested. Enjoy (￣︶￣*))")
        )
        await ctx.edit(content=f'Done ! {timer.total()}')

    except (InvalidARL, FileNotFoundError):
        await ctx.edit(
            content=('The Deezer ARL is not valid. '
                     'Please contact the developer or use a custom ARL.')
        )
    except TrackNotFound:
        await ctx.edit(
            content='Track not found on Deezer ! Try using another ARL.'
        )


set = bot.create_group(
    "set",
    "Change bot settings."
)


@set.command(
    name='default-music-format',
    description='Change your default music format.',
)
@discord.option(
    'format',
    type=discord.SlashCommandOptionType.string,
    description='The format of the files you want to save.',
    autocomplete=discord.utils.basic_autocomplete(
        ['FLAC', 'MP3 320', 'MP3 128']),
)
async def default_music_format(
    ctx: discord.ApplicationContext,
    format: str
) -> None:
    if format not in ['FLAC', 'MP3 320', 'MP3 128']:
        await ctx.respond('Please select a valid format !')
    else:
        await change_settings(
            ctx.author.id,
            'defaultMusicFormat',
            format
        )
        await ctx.respond('Your default music format '
                          f'has been set to {format} !')


@set.command(
    name='custom-arl',
    description='Change your Deezer localization.'
)
@discord.option(
    'country',
    type=discord.SlashCommandOptionType.string,
    description='Songs from this country should be more available.',
    autocomplete=discord.utils.basic_autocomplete(get_countries()),
)
async def custom_arl(
    ctx: discord.ApplicationContext,
    country: str
) -> None:
    arl = get_arl(country)
    await ctx.respond("Give me a second !")
    if arl:
        await change_settings(ctx.author.id, 'publicArl', arl)
        load_arl(ctx.user.id, arl=arl, force=True)
        await ctx.edit(
            content=f'You are now using a Deezer ARL from {country} !'
        )
    else:
        await ctx.edit(
            content=f"Sorry ! The country {country} isn't available."
        )


@set.command(
    name='default-arl',
    description='Change your Deezer localization.'
)
async def default_arl(ctx: discord.ApplicationContext) -> None:
    await ctx.respond("Give me a second !")
    await change_settings(ctx.author.id, 'publicArl', ARL)
    load_arl(ctx.user.id, arl=ARL, force=True)
    await ctx.edit(content="You are now using the default ARL !")


vc = bot.create_group(
    "vc",
    "Voice channel commands."
)


# From https://gist.github.com/aliencaocao/83690711ef4b6cec600f9a0d81f710e5
class Source:
    """Parent class of all music sources"""

    def __init__(self, audio_source: discord.AudioSource, metadata):
        self.audio_source: discord.AudioSource = audio_source
        self.metadata = metadata
        self.title: str = metadata.get('title', 'Unknown title')
        self.url: str = metadata.get('url', 'Unknown URL')

    def __str__(self):
        return f'{self.title} (<{self.url}>)'


class YTDLSource(Source):
    """Subclass of YouTube sources"""

    def __init__(self, audio_source: discord.AudioSource, metadata):
        super().__init__(audio_source, metadata)
        # yt-dlp specific key name for original URL
        self.url: str = metadata.get('webpage_url', 'Unknown URL')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        metadata = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )
        if 'entries' in metadata:
            metadata = metadata['entries'][0]
        filename = metadata['url'] if stream else ytdl.prepare_filename(
            metadata)
        return cls(await discord.FFmpegOpusAudio.from_probe(
            filename,
            **ffmpeg_options,
            ),
            metadata
        )


server_sessions = {}


class ServerSession:
    def __init__(self, guild_id: int, voice_client: discord.voice_client):
        self.guild_id = guild_id
        self.voice_client = voice_client
        self.queue = []

    def display_queue(
        self
    ) -> str:
        if not self.queue:
            return 'No songs in queue !'

        # Currently playing
        # Youtube
        if self.queue[0]['source'] == 'Youtube':
            elements = [
                f"Currently playing: {self.queue[0]['element']}\n"
            ]
        # Deezer
        else:
            elements = [
                ("Currently playing: "
                 f"{self.queue[0]['element']['display_name']}\n")
            ]

        # The actual list
        for i, s in enumerate(self.queue[1:], start=1):
            # Youtube
            if s['source'] == 'Youtube':
                elements.append(f"{i}. {s['element']}\n")
            # Deezer
            else:
                elements.append(f"{i}. {s['element']['display_name']}\n")

        return ''.join(elements)

    async def add_to_queue(
        self,
        ctx: discord.ApplicationContext,
        element: dict | str,
        source: str | None = None
    ) -> None:  # does not auto start playing the playlist
        # Basically element is a string is youtube, or a dict if from Deezer..
        if source == 'Youtube':
            yt_source = await YTDLSource.from_url(
                element,
                loop=bot.loop,
                stream=False
            )
            self.queue.append({'element': yt_source, 'source': source})
            if len(self.queue) > 1:
                await ctx.edit(
                    content=f'Added to queue: {yt_source.title} !')
        else:
            self.queue.append({'element': element, 'source': source})
            if len(self.queue) > 1:
                await ctx.edit(
                    content=f"Added to queue: {element['display_name']} !"
                )

    async def start_playing(
        self,
        ctx: discord.ApplicationContext
    ) -> None:
        source = self.queue[0]['source']
        if source == 'Youtube':
            await ctx.edit(
                content=f"Now playing: {self.queue[0]['element'].title}"
            )
            self.voice_client.play(
                self.queue[0]['element'].audio_source,
                after=lambda e=None: self.after_playing(ctx, e)
            )
        else:
            await ctx.edit(
                content=("Now playing: "
                         f"{self.queue[0]['element']['display_name']}")
            )
            self.voice_client.play(
                discord.FFmpegOpusAudio(
                    self.queue[0]['element']['path'],
                    bitrate=510,
                ),
                after=lambda e=None: self.after_playing(ctx, e)
            )

    def after_playing(
        self,
        ctx: discord.ApplicationContext,
        error: Exception
    ) -> None:
        if error:
            raise error
        else:
            if self.queue:
                asyncio.run_coroutine_threadsafe(
                    self.play_next(ctx),
                    bot.loop
                )

    # should be called only after making the
    # first element of the queue the song to play
    async def play_next(
        self,
        ctx: discord.ApplicationContext
    ) -> None:
        self.queue.pop(0)
        if self.queue:
            if self.queue[0]['source'] == 'Youtube':
                # Element: yt-dl element
                self.voice_client.play(
                    self.queue[0]['element'].audio_source,
                    after=lambda e=None: self.after_playing(ctx, e)
                )
            else:
                # Element: deezer element
                await ctx.send(
                    content=("Now playing: "
                             f"{self.queue[0]['element']['display_name']}")
                )
                self.voice_client.play(
                    discord.FFmpegOpusAudio(
                        self.queue[0]['element']['path'], bitrate=510),
                    after=lambda e=None: self.after_playing(ctx, e)
                )


@vc.command(
    name='join',
    description='Invite Ugoku in your voice channel !'
)
async def join(
    ctx: discord.ApplicationContext,
    channel: discord.VoiceChannel,
    predecessor: bool = False,
) -> None:
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
        if predecessor:
            await ctx.edit(
                content=f'Joined {ctx.voice_client.channel.name} !'
            )
        else:
            await ctx.respond(
                f'Joined {ctx.voice_client.channel.name} !'
            )

    else:
        await channel.connect()
        if predecessor:
            await ctx.edit(
                content=f'Joined {ctx.voice_client.channel.name} !'
            )
        else:
            await ctx.respond(
                f'Joined {ctx.voice_client.channel.name} !'
            )

    if ctx.voice_client.is_connected():
        server_sessions[ctx.guild.id] = ServerSession(
            ctx.guild.id,
            ctx.voice_client
        )
        return server_sessions[ctx.guild.id]
    else:
        await ctx.edit(content=f'Failed to connect to voice channel {ctx.user.voice.channel.name}.')


@vc.command(
    name='play',
    description='Select a song to play.'
)
@discord.option(
    'url',
    type=discord.SlashCommandOptionType.string,
    description='Deezer or Spotify url of a song.'
)
async def play(
    ctx: discord.ApplicationContext,
    url: str
) -> None:
    await ctx.respond(f'Connecting to Deezer...')
    if url:
        try:
            # Download
            arl = get_setting(
                ctx.author.id,
                'publicArl',
                ARL
            )
            print('current arl', arl)
            print('current arl', arl)
            print('current arl', arl)
            downloadObjects, _ = init_dl(
                url=url,
                user_id=ctx.user.id,
                arl=arl,
                brfm='flac',
                settings=vc_settings
            )
            dz = load_arl(ctx.user.id, arl)
            await ctx.edit(content=f'Getting the song...')
            all_data = await download_links(
                dz,
                downloadObjects,
                settings=vc_settings
            )
            info_dict = all_data[0]
            if not downloadObjects:
                raise TrackNotFound

            # Join
            guild_id = ctx.guild.id
            if guild_id not in server_sessions or not ctx.user.voice:
                # not connected to any VC
                if ctx.user.voice is None:
                    await ctx.edit(
                        content=f'You are not connected to any voice channel !'
                    )
                    return
                else:
                    session: ServerSession = await join(
                        ctx,
                        ctx.user.voice.channel,
                        predecessor=True
                    )

            else:  # is connected to a VC
                session = server_sessions[guild_id]
                if session.voice_client.channel != ctx.user.voice.channel:
                    # connected to a different VC than the command issuer
                    # (but within the same server)
                    await session.voice_client.move_to(ctx.user.voice.channel)
                    await ctx.send(f'Connected to {ctx.user.voice.channel}.')

            await session.add_to_queue(ctx, info_dict)
            if not session.voice_client.is_playing() and len(session.queue) <= 1:
                await session.start_playing(ctx)

        except TrackNotFound:
            await ctx.edit(
                content='Track not found on Deezer ! Try using another ARL.'
            )
    else:
        ctx.respond('wut duh')


@vc.command(
    name='pause',
    description='Pause the current song.'
)
async def pause(ctx: discord.ApplicationContext):
    guild_id = ctx.guild.id
    if guild_id in server_sessions:
        voice_client = server_sessions[guild_id].voice_client
        if voice_client.is_playing():
            voice_client.pause()
            await ctx.respond('Paused !')


@vc.command(
    name='resume',
    description='Resume the current song.'
)
async def resume(ctx: discord.ApplicationContext):
    guild_id = ctx.guild.id
    if guild_id in server_sessions:
        voice_client = server_sessions[guild_id].voice_client
        if voice_client.is_paused():
            voice_client.resume()
            await ctx.respond('Resumed !')


@vc.command(
    name='skip',
    description='Skip the current song.'
)
async def skip(ctx: discord.ApplicationContext):
    guild_id = ctx.guild.id
    if guild_id in server_sessions:
        session = server_sessions[guild_id]
        voice_client = session.voice_client
        if voice_client.is_playing():
            if len(session.queue) > 1:
                voice_client.stop()
                await ctx.respond('Skipped !')
            else:
                await ctx.respond('This is the last song in queue !')


@vc.command(
    name='queue',
    description='Show the current queue.'
)
async def show_queue(ctx: discord.ApplicationContext):
    guild_id = ctx.guild.id
    if guild_id in server_sessions:
        print('queue:', server_sessions[guild_id].display_queue())
        await ctx.respond(
            f'{server_sessions[guild_id].display_queue()}'
        )


@vc.command(
    name='clear',
    description='Clear the queue and stop current song.'
)
async def clear(
    ctx: discord.ApplicationContext
):
    guild_id = ctx.guild.id
    if guild_id in server_sessions:
        voice_client = server_sessions[guild_id].voice_client
        server_sessions[guild_id].queue = []
        if voice_client.is_playing():
            voice_client.stop()
        await ctx.send('Queue cleared !')


@vc.command(
    name='leave',
    description='Nooooo （＞人＜；）')
async def leave(
    ctx: discord.ApplicationContext
):
    guild_id = ctx.guild.id
    if guild_id in server_sessions:
        voice_client = server_sessions[guild_id].voice_client
        await voice_client.disconnect()
        voice_client.cleanup()
        del server_sessions[guild_id]
        await ctx.respond(f'Baibai !')


@vc.command(
    name='bitrate',
    description='Get the bitrate of the voice channel you are in.',
)
async def channel_bitrate(
    ctx: discord.ApplicationContext
) -> None:
    if ctx.author.voice:
        await ctx.respond(f'{ctx.author.voice.channel.bitrate//1000}kbps.')
    else:
        await ctx.respond(f'You are not in a voice channel !')


# Still mainly from
# https://gist.github.com/aliencaocao/83690711ef4b6cec600f9a0d81f710e5
# For Ika and Laser xD
@vc.command(
    name='play-from-youtube',
    description='Play any videos from Youtube !'
)
@discord.option(
    'query',
    type=discord.SlashCommandOptionType.string,
    description='URL or a search query.'
)
async def play_from_youtube(
    ctx: discord.ApplicationContext,
    query: str
):
    await ctx.respond('Give me a second !')
    guild_id = ctx.guild.id
    # not connected to any VC
    if guild_id not in server_sessions or not ctx.user.voice:
        if ctx.user.voice is None:
            await ctx.edit(
                content=f'You are not connected to any voice channel !'
            )
            return
        else:
            session: ServerSession = await join(
                ctx,
                ctx.user.voice.channel,
                predecessor=True
            )
    else:  # is connected to a VC
        session = server_sessions[guild_id]
        # connected to a different VC than the command issuer (but within the same server)
        if session.voice_client.channel != ctx.user.voice.channel:
            await session.voice_client.move_to(ctx.user.voice.channel)
            await ctx.edit(content=f'Connected to {ctx.user.voice.channel} !')

    try:
        await ctx.edit(content='Downloading the audio...')
        requests.get(query)

    # if not a valid URL, do search and play the first video in search result
    except (requests.exceptions.InvalidURL, requests.exceptions.MissingSchema):
        query_string = urllib.parse.urlencode({"search_query": query})
        formatUrl = urllib.request.urlopen(
            "https://www.youtube.com/results?" + query_string)
        search_results = re.findall(
            r"watch\?v=(\S{11})", formatUrl.read().decode())
        url = f'https://www.youtube.com/watch?v={search_results[0]}'

    except requests.exceptions.InvalidSchema:
        await ctx.edit(content=f'Hmm it seems like the URL is not valid!')

    else:  # is a valid URL, play directly
        url = query
    # will download file here
    await session.add_to_queue(ctx, url, source='Youtube')
    if not session.voice_client.is_playing() and len(session.queue) <= 1:
        await session.start_playing(ctx)

# End of vc commands


@bot.command(
    name='talk',
    description='!'
)
@discord.option(
    'message',
    type=discord.SlashCommandOptionType.string,
    description='A message you want me to read !'
)
async def talk(
    ctx: discord.ApplicationContext,
    message: str
) -> None:
    await ctx.send(message)


bot.run(DEV_TOKEN)
