import discord
from discord.ext import commands
import yt_dlp
import asyncio

import urllib
import re
import logging
import os
from time import sleep, gmtime
from datetime import datetime
from dotenv import load_dotenv
from bot.line import get_stickerpack
from bot.downloader import *
from bot.exceptions import *
from bot.settings import *
from bot.arls import *
from bot.timer import Timer
from typing import Any
from bot.search import get_song_url, is_url, A_ISO3166
from bot.spotify import SpotifyDownloader

load_dotenv()

# Make chatbot module optional

API_KEY = os.getenv('OPENAI_API_KEY')
if API_KEY:
    from bot.chatbot import Chat, active_chats
else:
    print('No OpenAI API key found, chatbot module disabled.')  # just a small reminder



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

# INIT BOT
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents)

# VARIABLES
TOKEN = os.getenv('DISCORD_TOKEN')
DEV_TOKEN = os.getenv('DEV_TOKEN')
ARL = os.getenv('DEEZER_ARL')
ARL_COUNTRY = os.getenv('ARL_COUNTRY')
OWNER_ID = int(os.getenv('OWNER_ID'))
g_arl_info = {'arl': ARL, 'country': ARL_COUNTRY}
sd = SpotifyDownloader()
arl_countries = get_countries()

# Only for chatbot (for now)
whitelisted_servers: list = get_list('whitelistedServers')

# VC deemix settings: ignore tags and download only the song itself
# Init settings
vc_config_path = Path('.') / 'deemix' / 'vc_config'
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
    description='URL of a sticker pack from LINE Store.'
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
    gif: bool = True
) -> None:
    timer = Timer()

    if not url:
        await ctx.respond(
            'Please specify an URL to a sticker pack. '
            'E.g: https://store.line.me/stickershop/product/1472670/'
        )
    else:
        await ctx.respond(f'Give me a second !')
        try:
            zip_file = get_stickerpack(url, gif=gif)
        except IncorrectURL:
            await ctx.edit(content='Invalid URL ! Please check again.')
            return
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
    'query',
    type=discord.SlashCommandOptionType.string,
    description=(
        'Spotify/Deezer URL or a query of a song. Separate urls with '
        'semi-colons.'
    )
)
@discord.option(
    'format',
    type=discord.SlashCommandOptionType.string,
    description='The format of the files you want to save.',
    autocomplete=discord.utils.basic_autocomplete(
        ['FLAC', 'MP3 320', 'MP3 128'])
)
async def songs(
    ctx: discord.ApplicationContext,
    query: str,
    format: str | int | None = None,
) -> None:
    index = {'FLAC': 0, 'MP3 320': 1, 'MP3 128': 2}
    timer = Timer()

    await ctx.respond(f'Give me a second !')
    arl_info: dict = get_setting(
        ctx.author.id,
        'publicArl',
        g_arl_info
    )
    # Not an url ? Then get it !
    if is_url(query, sites=['spotify', 'deezer']):
        url = query
    else:
        url = get_song_url(query, dz=dz)
        if not url:
            await ctx.edit(content='Track not found on Deezer !')
            return

    if format not in index:
        format = get_setting(
            ctx.user.id,
            'defaultMusicFormat',
            'MP3 320'
        )
    try:
        success = False
        i = index[format]
        formats = ['FLAC', 'MP3 320', 'MP3 128']

        while not success:
            path = await complete_dl(
                ctx=ctx,
                url=url,
                arl_info=arl_info,
                timer=timer,
                format=formats[i]
            )
            size = os.path.getsize(path)
            if size < ctx.guild.filesize_limit:
                success = True
            elif i >= len(formats) - 1:
                await ctx.edit(content='Track too heavy ーへー')
                return
            else:
                i += 1
                await ctx.send(
                    'Track too heavy, '
                    f'trying the following format: {formats[i]}.'
                )

        logging.info(f'Chosen format: {format}')
        logging.info(f'File size: {size}, Path: {path}')

        # SUCESS:
        await ctx.edit(
            content=f'Download finished, {timer.round()}. Uploading...'
        )
        await ctx.send(
            file=discord.File(path),
            content=(
                f"Sorry for the wait <@{ctx.author.id}> ! "
                "Here's the song(s) you requested. Enjoy (￣︶￣*))"
            )
        )
        await ctx.edit(content=f'Done ! {timer.total()}')

    except InvalidARL:
        await ctx.edit(
            content=(
                'The Deezer ARL is not valid. '
                'Please contact the developer or use a custom ARL.'
            )
        )
    except TrackNotFound:
        await ctx.edit(
            content='Track not found on Deezer !'
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
    description='Change your Deezer location.'
)
@discord.option(
    'country',
    type=discord.SlashCommandOptionType.string,
    description='Songs from this country should be more available.',
    autocomplete=discord.utils.basic_autocomplete(arl_countries),
)
async def custom_arl(
    ctx: discord.ApplicationContext,
    country: str
) -> None:
    arl = get_arl(country)
    await ctx.respond("Give me a second !")
    if arl:
        iso_country = A_ISO3166[country]
        await change_settings(
            ctx.author.id,
            'publicArl',
            {'arl': arl, 'country': iso_country}
        )
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
    await change_settings(
        ctx.author.id,
        'publicArl', {"arl": ARL, "country": ARL_COUNTRY}
    )
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
            title = self.queue[0]['element']
        # Deezer or Spotify
        else:
            title = self.queue[0]['element']['display_name']
        elements = [
            "Currently playing: "
            f"{title} ({self.queue[0]['source']})\n"
        ]

        # The actual list
        for i, s in enumerate(self.queue[1:], start=1):
            # Youtube
            if s['source'] == 'Youtube':
                title = s['element']
            # Deezer or Spotify
            else:
                title = s['element']['display_name']
            elements.append(f"{i}. {title} ({s['source']})\n")

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
) -> None:
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()

    if ctx.voice_client.is_connected():
        server_sessions[ctx.guild.id] = ServerSession(
            ctx.guild.id,
            ctx.voice_client
        )
        return server_sessions[ctx.guild.id]
    else:
        await ctx.edit(content=f'Failed to connect to voice channel {ctx.user.voice.channel.name}.')


async def connect(ctx: discord.ApplicationContext) -> ServerSession | None:
    guild_id = ctx.guild.id
    if guild_id not in server_sessions or not ctx.user.voice:
        # not connected to any VC
        if ctx.user.voice is None:
            await ctx.respond(
                content=f'You are not connected to any voice channel !'
            )
            return
        else:
            session: ServerSession = await join(
                ctx,
                ctx.user.voice.channel
            )

    else:  # is connected to a VC
        session = server_sessions[guild_id]
        if session.voice_client.channel != ctx.user.voice.channel:
            # connected to a different VC than the command issuer
            # (but within the same server)
            await session.voice_client.move_to(ctx.user.voice.channel)

    return session


async def play_deezer(ctx: discord.ApplicationContext, query: str) -> None:
    # Join
    session: ServerSession | None = await connect(ctx)
    if not session:
        return

    await ctx.respond(f'Connecting to Deezer...')
    if query:
        # Connecting
        arl_info = get_setting(
            ctx.author.id,
            'publicArl',
            g_arl_info
        )
        dz = load_arl(ctx.user.id, arl_info['arl'])
        await ctx.edit(content=f'Getting the song...')

        # Not an url ? Then get it !
        if is_url(query, sites=['spotify', 'deezer']):
            url = query
        else:
            url = get_song_url(query, dz=dz)
            if not url:
                raise TrackNotFound

        # Actual downloading
        format = 'FLAC'
        downloadObjects = init_dl(
            url=url,
            user_id=ctx.user.id,
            arl_info=arl_info,
            format=format,
            settings=vc_settings
        )
        all_data = await download_links(
            dz,
            downloadObjects,
            settings=vc_settings,
            ctx=ctx,
            format=format
        )
        info_dict = all_data[0]
        if not downloadObjects:
            raise TrackNotFound

        await session.add_to_queue(ctx, info_dict, source='Deezer')
        if not session.voice_client.is_playing() and len(session.queue) <= 1:
            await session.start_playing(ctx)


async def play_spotify(ctx: discord.ApplicationContext, url: str) -> None:
    # Connect
    # Play songs only if user is in a voice channel
    session: ServerSession | None = await connect(ctx)
    if not session:
        return

    await ctx.respond('Give me a second !')
    # Problem: have to wait to dl EVERYTHING before playing
    all_data = sd.from_url(url)
    first_info_dict = all_data.pop(0)
    await session.add_to_queue(ctx, first_info_dict, source='Spotify')

    if not session.voice_client.is_playing() and len(session.queue) <= 1:
        await session.start_playing(ctx)

    for info_dict in all_data:
        await session.add_to_queue(ctx, info_dict, source='Spotify')


@vc.command(
    name='play',
    description='Select a song to play.'
)
@discord.option(
    'query',
    type=discord.SlashCommandOptionType.string,
    description='Deezer (if source)/Spotify URL or a search query of a song.'
)
@discord.option(
    'source',
    type=discord.SlashCommandOptionType.string,
    description='Source of the song (Deezer: better audio, Spotify: better library).',
    autocomplete=discord.utils.basic_autocomplete(
        ['Deezer', 'Spotify']),
)
async def play(
    ctx: discord.ApplicationContext,
    query: str,
    source: str
) -> None:
    if source == 'Deezer':
        try:
            await play_deezer(ctx, query)
        except TrackNotFound:
            await ctx.edit(
                content='Track not found on Deezer !'
            )

    elif source == 'Spotify':
        try:
            await play_spotify(ctx, query)
        except FileNotFoundError as e:
            await ctx.edit(content='Invalid URL ! Please try again.')
    else:
        await ctx.respond('wut duh')


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
        session: ServerSession = server_sessions[guild_id]
        print('queue:', session.display_queue())
        await ctx.respond(f'{session.display_queue()}')


@vc.command(
    name='remove',
    description='Remove a song in queue.'
)
@discord.option(
    'index',
    type=discord.SlashCommandOptionType.integer,
    description=' Index of the song in the queue (1, 2...).'
)
async def remove(
    ctx: discord.ApplicationContext,
    index: int
) -> None:
    id = ctx.guild.id
    if ctx.guild.id in server_sessions:
        if index == 0:
            await ctx.respond(
                "You can't skip the current song ! "
                "Try to use /skip ~"
            )
        elif index >= len(server_sessions[id].queue):
            await ctx.respond(f'https://tenor.com/view/chocola-nekopara-hnzk-gif-26103729 ')
        else:
            removed = server_sessions[id].queue.pop(index)
            await ctx.respond(f'Removed {removed} from queue !')


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
        await ctx.respond('Queue cleared !')


@vc.command(
    name='leave',
    description='Nooooo （＞人＜；）')
async def leave(
    ctx: discord.ApplicationContext
):
    guild_id = ctx.guild.id
    if guild_id in server_sessions:
        voice_client: discord.voice_client.VoiceClient = server_sessions[guild_id].voice_client
        await voice_client.disconnect()
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
) -> None:
    # Connect
    session: ServerSession | None = await connect(ctx)
    if not session:
        return

    await ctx.respond('Give me a second !')
    try:
        await ctx.edit(content='Downloading the audio...')
        if is_url(query, sites=['youtube.com', 'youtu.be']):
            requests.get(query)

        # if not a valid URL, do search and play the first video in search result
        else:
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
    # logging.info(f'{ctx.author.name} used /talk: "{message}"')
    # :aAzusaLaugh:
    await ctx.send(message)
    await ctx.respond('Done !', ephemeral=True)     # remove the annoying 'the application does not respond' message


@bot.command(
    name='debug',
    description='debug'
)
@discord.option(
    'code',
    type=discord.SlashCommandOptionType.string,
)
async def debug(
    ctx: discord.ApplicationContext,
    code: str
) -> None:
    if ctx.author.id == OWNER_ID:
        await ctx.respond(eval(code))

################ CHATBOT ################

# So here I use the old method (Events) to make the chatbot, just because
# It allows a more fluent chat

if API_KEY:  # api key is given
    def can_use_chatbot(message: discord.Message):
        return (
            message.content.startswith('-')
            and message.guild.id in whitelisted_servers
            # and message.author.id not in get_blacklisted_users()
        )


    def generate_response(message: discord.message, chat: Chat) -> str:
        image_urls = []
        processed_message: str = message.content

        # IMAGE
        if message.attachments:
            # Grab the link of the images
            for attachment in message.attachments:
                if "image" in attachment.content_type:
                    image_urls.append(attachment.url)

        # EMOTES
        # Only grabs the first emote, would be too expensive otherwise..
        has_emote = False
        result: re.Match = re.search('<(.+?)>', processed_message)
        if result:
            emote = result.group(0)
            nums = re.findall(r'\d+', emote)
            name: re.Match = re.search(':(.+?):', processed_message)
            if nums:
                snowflake = nums[-1]
                processed_message = processed_message.replace(
                    emote, name.group(0))
                has_emote = True

        if has_emote:
            url = f'https://cdn.discordapp.com/emojis/{snowflake}.png'
            image_urls.append(url)

        # STICKERS
        if message.stickers:
            sticker: discord.StickerItem = message.stickers[0]
            image_urls.append(sticker.url)

        # REPLY
        reply = chat.prompt(
            user_msg=processed_message[1:],
            username=message.author.display_name,
            image_urls=image_urls
        )
        return reply


    @bot.event
    async def on_message(
        message: discord.Message
    ) -> None:
        if can_use_chatbot(message):
            # Create a new chat if needed
            if not message.guild.id in active_chats:
                Chat(message.guild.id)
            chat: Chat = active_chats[message.guild.id]

            if '-draw' in message.content.lower():
                results = chat.draw(message.content, message.author.display_name)
                await message.channel.send(results['image_url'])
                await message.channel.send(results['reply'])
            else:
                reply = generate_response(message, chat)
                await message.channel.send(reply)


################ HELP SECTION ################
# EMBEDS
general = discord.Embed(
    title='Help',
    description=('*Hello ! My name is Yur-, I mean Ugoku !'
                 ' a bot created by Shewi ~ \n Always ready to help !*'),
    color=discord.Colour.from_rgb(241, 219, 199),
)
general.add_field(
    name='Sources',
    value=(
        '> - The character is **Yuruneko**, an OG character designed and '
        'drawn by [しろなっぱ](https://x.com/shironappa_) (Shironappa). '
        'Please support her ! \n'
        '> - The music player code has been adapted from this '
        '[github gist](https://gist.github.com/aliencaocao/83690711ef4b6cec600f9a0d81f710e5).\n'
        '> - The bot has been coded using Pycord and Deemix. You can '
        'find the code source '
        '[here](https://github.com/Shewiiii/Ugoku-bot).'
    )
)
general.add_field(
    name='Features',
    value=(
        '> Ugoku ! can:\n'
        '> - Download stickers from LINE\n'
        '> - Download songs from Deezer, losslessly and from almost any '
        'country\n'
        '> - Play music in voice channels, with '
        'the highest achievable audio quality (Opus 510 kbps '
        'single-pass compression)\n'
        '> - Play the audio of a video from Youtube in voice channels\n'
        '> - Talk ?\n'
        '> - ...And more to come !'
    ),
    inline=False
)

general.set_footer(text="ネコ・アリウスって呼んでもいいよ～")
# footers can have icons too
general.set_thumbnail(
    url="https://cdn.discordapp.com/attachments/1193547778689863682/1254587281143234672/6.png?ex=667a08f4&is=6678b774&hm=8aebab3e7f0b6df7b2d2c2abb444e8d36a926ffce3e905e489763198245a7430&")
general.set_image(url="")

commands = discord.Embed(
    title="Commands",
    description='Here is the list of commands you can use.',
    # Pycord provides a class with default colors you can choose from
    color=discord.Colour.from_rgb(241, 219, 199),
)
commands.add_field(
    name='Get',
    value=(
        '> [/get stickers](http://example.com/) - Uploads a sticker '
        'pack from LINE, from a given LINE STORE URL. Animated PNGs are '
        'converted to GIF by default.\n'
        '> \n'
        '> [/get songs](http://example.com/) - Uploads a song, with one '
        'of the following available formats: MP3 128 kbps, MP3 320 kbps, '
        'FLAC. Supports multiple URLs, but please note that if '
        'the file size exceeds what is allowed by the server, the file '
        'will not be sent.'
    )
)
commands.add_field(
    name='Set',
    value=(
        '> [/set default-music-format](http://example.com/) - '
        'Defines the format in which you want to receive music files '
        'by default.\n'
        '> \n'
        '> [/set default-arl](http://example.com/) - Changes your '
        'Deezer location to the default one: France.\n'
        '> \n'
        '> [/set custom-arl](http://example.com/) - Changes your '
        'Deezer location to an available country of your choice. '
        'Useful if most of your music is geographically blocked in France. '
        'Ugoku ! will automatically search for another location, but this '
        'may take some time.'
    ),
    inline=False
)
commands.add_field(
    name='Voice channels',
    value=(
        '> [/vc join](http://example.com/) - Invites Ugoku ! in your vc.\n'
        '> \n'
        '> [/vc play](http://example.com/) - Plays a song of your choice. '
        'If a song is already playing, adds the song to queue.\n'
        '> \n'
        '> [/vc play-from-youtube](http://example.com/) - Plays the audio of '
        'a video of your choice. If a song is already playing, adds the '
        'video to queue.\n'
        '> \n'
        '> [/vc pause](http://example.com/) - Pauses the song.\n'
        '> \n'
        '> [/vc resume](http://example.com/) - Resumes the song.\n'
        '> \n'
        '> [/vc skip](http://example.com/) - Skips the currently playing '
        'song.\n'
        '> \n'
        '> [/vc queue](http://example.com/) - Shows the queue of remaining '
        'songs.\n'
        '> \n'
        '> [/vc remove](http://example.com/) - Removes a song in queue by '
        'index (1, 2...).\n'
        '> \n'
        '> [/vc clear](http://example.com/) - Clears the queue and stops '
        'current song.\n'
        '> \n'
        '> [/vc leave](http://example.com/) - Leave Ugoku ! from the vc.\n'
        '> \n'
        '> [/vc bitrate](http://example.com/) - Shows bitrate of the vc '
        'you are in. Vc bitrate does not affect sound quality, as it '
        'bypasses it.'
    ),
    inline=False
)
commands.add_field(
    name='Miscellaneous',
    value=(
        '> [/ping](http://example.com/) - Shows the ping of Ugoku !\n'
        '> \n'
        '> [/talk](http://example.com/) - *なに～* '
        '<:ugoku_yummy:1238139232913199105>\n'
        '> \n'
        '> [Ugoku](http://example.com/) - Try to start a sentence '
        'with - !\n'
    ),
    inline=False
)


# VIEW/BUTTONS
class MyView(discord.ui.View):
    @discord.ui.button(
        label="General",
        style=discord.ButtonStyle.secondary,
    )
    async def general_callback(self, button, interaction):
        await interaction.response.edit_message(
            embed=general
        )

    @discord.ui.button(
        label="Commands",
        style=discord.ButtonStyle.secondary,
    )
    async def commands_callback(self, button, interaction):
        await interaction.response.edit_message(
            embed=commands
        )


# COMMAND
@bot.command(
    name='help',
    description='ﾁﾗｯ'
)
async def help(ctx: discord.ApplicationContext):
    await ctx.respond(
        embed=general,
        view=MyView()
    )

bot.run(DEV_TOKEN)
